# SIEM (Wazuh) — recolección de logs y alarmas

FakeEnv centraliza **todos** los logs en `./logs/` y un **Wazuh Manager** los
ingiere, decodifica y genera **alarmas**.

## Arquitectura

```
                      ./logs/                          siem/  (Wazuh Manager)
 Flask (gunicorn) ──► logs/app/fakenv.log  ─┐
                  └─► logs/app/sql.log       │   localfile (json)   ┌────────────┐
 nginx           ──► logs/nginx/*.log        ├──────────────────►  │  decoders  │
 Drupal/Apache   ──► logs/drupal/apache/*    │   localfile (apache) │  + reglas  │
 MariaDB         ──► logs/drupal/mariadb/*   ┘   localfile (mysql)  │  (custom)  │
                                                                     └─────┬──────┘
                                                                           ▼
                                                       /var/ossec/logs/alerts/alerts.json
```

| Fuente | Fichero | Qué contiene |
|--------|---------|--------------|
| App (eventos) | `logs/app/fakenv.log` | peticiones HTTP, login OK/fallido, IDOR, SSTI, volcado de telemetría, alta/baja de usuarios, subida de ficheros, acceso a `/.env`, excepciones |
| App (BD SQLite) | `logs/app/sql.log` | **todas** las sentencias SQL (vía SQLAlchemy) |
| Web | `logs/nginx/access.log`,`error.log` | toda petición a la app (formato combined) |
| Blog | `logs/drupal/apache/*` | Apache del Drupal |
| Blog (BD) | `logs/drupal/mariadb/general.log`,`error.log` | todas las queries de MariaDB |

## Puesta en marcha

### 1. App detrás de nginx (gunicorn)

```bash
python seed.py                       # crea fakenv.db (si no está)
docker compose up -d --build         # web (gunicorn) + nginx  ->  http://localhost:8000
```
Los logs aparecen en `logs/app/` y `logs/nginx/`.

> Modo desarrollo alternativo (sin Docker): `python run.py` (sirve en :5000 y
> también escribe en `logs/app/`).

### 2. Blog Drupal con logs (opcional)

```bash
mkdir -p logs/drupal/mariadb && chmod 777 logs/drupal/mariadb   # permiso para MariaDB
cd docker && docker compose up -d --build
docker compose exec drupal bash /seed/seed_blog.sh              # solo la 1ª vez
```

### 3. Wazuh Manager (recolector + alarmas)

```bash
cd siem && docker compose up -d
# ver las alarmas en vivo:
docker compose exec wazuh.manager tail -f /var/ossec/logs/alerts/alerts.json
```

## Generar alarmas (probar la detección)

Con la app en `http://localhost:8000`, lanza alguno de los ataques del laboratorio:

| Acción | Regla / alarma |
|--------|----------------|
| 5+ logins fallidos seguidos | `100102` fuerza bruta |
| `/dashboard/invoice?id_factura=7` (factura ajena) | `100110` IDOR |
| Telemetría con fecha inválida (`desde=hola`) | `100111` volcado por excepción |
| Abrir `/.env` | `100112` acceso a fichero sensible |
| `OR '1'='1` en una query (Drupalgeddon en MariaDB) | reglas web/SQL integradas + `100130` |

Cada coincidencia genera una entrada en `alerts.json` con la regla, el nivel y
los campos del evento.

## Dashboard web (opcional)

El Manager por sí solo ya recoge y alarma. Para la **UI** de Wazuh (Indexer +
Dashboard, ~3-4 GB RAM extra) se despliega el stack *single-node* oficial de
[wazuh-docker](https://github.com/wazuh/wazuh-docker) y se le añade nuestro
`siem/config/ossec.conf` y `local_rules.xml`.

## Reglas a medida

En `siem/config/local_rules.xml` (IDs 100100–100130). Tras editarlas:
`cd siem && docker compose restart wazuh.manager`.
