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

## Puesta en marcha (un solo comando)

Todo se levanta desde el **único** `docker-compose.yml` de la raíz:

```bash
# 1) preparar carpetas de logs (MariaDB necesita escritura)
mkdir -p logs/app logs/nginx logs/drupal/apache logs/drupal/mariadb
chmod 777 logs/drupal/mariadb

# 2) BD de la app y arranque de TODO (app+nginx, blog, SIEM)
docker compose run --rm web python seed.py
docker compose up -d --build

# 3) contenido del blog (solo la 1ª vez)
docker compose exec drupal bash /seed/seed_blog.sh

# 4) ver las alarmas en vivo
docker compose exec wazuh tail -f /var/ossec/logs/alerts/alerts.json
```

- App: <http://localhost:8000> · Blog: <http://localhost:8080>
- Parar / arrancar: `docker compose stop` / `docker compose start`.

> Modo desarrollo alternativo (sin Docker): `python run.py` (sirve en :5000 y
> también escribe en `logs/app/`).

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
`docker compose restart wazuh`.
