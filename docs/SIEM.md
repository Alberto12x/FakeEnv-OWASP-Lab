# SIEM (Wazuh) — recolección de logs y alarmas

FakeEnv centraliza **todos** los logs en `./logs/` y un **stack Wazuh
single-node** (Manager + Indexer + Dashboard) los ingiere, decodifica, genera
**alarmas** y las muestra en una **interfaz web**.

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
- **Dashboard Wazuh: <https://localhost> (admin / `SecretPassword`)** — certificado
  autofirmado, el navegador avisará; acepta y entra.
- Parar / arrancar: `docker compose stop` / `docker compose start`.

> La **primera vez**, el servicio `wazuh_certs` genera los certificados TLS en
> `siem/config/wazuh_indexer_ssl_certs/` (sale con código 0). En arranques
> posteriores detecta que ya existen y no los regenera. El Indexer pide ~1 GB de
> RAM y el Dashboard tarda ~1 min en estar disponible tras el arranque.

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
| `OR '1'='1` en una query (Drupalgeddon en MariaDB) | reglas web/SQL **integradas** de Wazuh |

Cada coincidencia genera una entrada en `alerts.json` con la regla, el nivel y
los campos del evento.

## Dashboard web

La interfaz de Wazuh está integrada en el stack (basada en el *single-node*
oficial de [wazuh-docker](https://github.com/wazuh/wazuh-docker)). Tres servicios:

| Servicio | Imagen | Rol |
|----------|--------|-----|
| `wazuh` | wazuh-manager:4.9.0 | ingesta logs, decodifica, dispara reglas → `alerts.json` |
| `wazuh_indexer` | wazuh-indexer:4.9.0 | almacena y busca las alarmas (OpenSearch) |
| `wazuh_dashboard` | wazuh-dashboard:4.9.0 | UI web en <https://localhost> |

En la UI: *Threat Hunting* / *Security events* lista las alarmas; filtra por
`rule.id: 1001*` para ver solo las de FakeEnv.

## Configuración

| Fichero | Contenido |
|---------|-----------|
| `siem/config/wazuh_cluster/wazuh_manager.conf` | config del Manager + `localfile` de cada fuente de FakeEnv (sustituye a `ossec.conf` vía `/wazuh-config-mount`) |
| `siem/config/local_rules.xml` | reglas a medida (IDs 100100–100120) |
| `siem/config/certs.yml` | nodos para el generador de certificados TLS |
| `siem/config/wazuh_indexer/`, `wazuh_dashboard/` | config de OpenSearch y de la UI |

Tras editar reglas o config: `docker compose restart wazuh`.
