# Arquitectura — FakeEnv (TFM / OWASP)

Documento de arquitectura del laboratorio **FakeEnv**: web de una empresa
ficticia de ingeniería medioambiental, **deliberadamente vulnerable**, con un
blog **Drupal 7.30** y un **SIEM (Wazuh)** que recoge logs de todos los
componentes y genera alarmas.

> ⚠️ Software inseguro a propósito. No desplegar en Internet.

---

## 1. Visión general

FakeEnv se compone de **tres subsistemas independientes** que se integran a
través de una **carpeta de logs compartida** (`./logs/`), no por red:

1. **App FakeEnv** — Python/Flask tras nginx + gunicorn (web de clientes y panel
   de administración). BD SQLite.
2. **Blog** — Drupal 7.30 sobre PHP 5.6 + MariaDB (componente legacy vulnerable).
3. **SIEM** — Wazuh Manager que ingiere los logs de los otros dos y alarma.

---

## 2. Arquitectura lógica

### 2.1 Patrones y capas

- **Application Factory** (`create_app()` en `app/__init__.py`): construye la app
  desde una única clase de configuración (`config.py`) y conecta extensiones,
  blueprints, contexto y logging.
- **Blueprints** (modularidad por dominio).
- **ORM** con SQLAlchemy (modelos desacoplados del motor: SQLite por defecto,
  MySQL opcional vía `DATABASE_URL`).
- **Frontend** en HTML/CSS/JS *vanilla* (sin frameworks, por claridad didáctica;
  las gráficas de tendencias son SVG generado en servidor).

```
┌───────────────────────── App FakeEnv (Flask) ─────────────────────────┐
│  Presentación   Jinja2 (templates/) + CSS/JS vanilla                   │
│  ───────────────────────────────────────────────────────────────────  │
│  Controladores  blueprints/                                            │
│     main (/)        auth (/login…)   dashboard (/dashboard)  admin (/admin) │
│  ───────────────────────────────────────────────────────────────────  │
│  Servicios      security.py (hash MD5)   auth_utils.py (sesión+roles)  │
│                 logging_config.py (logs JSON)   constants.py           │
│  ───────────────────────────────────────────────────────────────────  │
│  Datos (ORM)    models/  User · Property · Invoice · Telemetry         │
│  ───────────────────────────────────────────────────────────────────  │
│  Extensiones    Flask-SQLAlchemy · Flask-Migrate                       │
└────────────────────────────────────────────────────────────────────────┘
              │ escribe                              ▲ lee (config)
              ▼                                      │
        logs/app/*.log (JSON)                   SQLite  fakenv.db
```

### 2.2 Blueprints (rutas)

| Blueprint | Prefijo | Responsabilidad |
|-----------|---------|-----------------|
| `main` | `/` | Web pública + catch-all que sirve ficheros del proyecto (vuln) |
| `auth` | `/login`, `/logout`, `/forgot` | Login (sin rate-limit/MFA), recuperación por pregunta de seguridad |
| `dashboard` | `/dashboard` | Panel cliente: facturas (IDOR), inmuebles, tendencias (SVG), telemetría (filtro), perfil (SSTI + subida cruda), export CSV |
| `admin` | `/admin` | Panel admin: usuarios (alta/baja), facturas, telemetría globales |

### 2.3 Modelo de datos

```
User 1───* Property 1───* Telemetry        (agua / electricidad / temperatura)
  │                ▲
  │                └── property_id (nullable)
  └──────* Invoice
  └──────* Telemetry  (user_id)
```

- **User**: credenciales (MD5+salt), rol (`user`/`admin`), pregunta/respuesta de
  seguridad (texto plano), datos personales.
- **Property** (inmueble): alias, dirección, tipo, m².
- **Invoice**: factura mensual (consumos, importe, estado).
- **Telemetry**: lectura diaria por métrica, ligada a usuario e inmueble.

### 2.4 Seguridad y sesión (lógica)

- Estado de sesión = `user_id` en la cookie firmada de Flask.
- Control de acceso por decoradores `login_required` / `admin_required`.
- **Nota**: varios puntos son inseguros a propósito (IDOR sin comprobación de
  propietario, fail-open por excepción, MD5, etc.). Detalle en `README.md` §1.

### 2.5 Observabilidad (logging → SIEM)

`app/logging_config.py` emite **JSON por línea**:

- `logs/app/fakenv.log` — toda petición HTTP + eventos de seguridad
  (`log_event`): login OK/fallido, IDOR, volcado de telemetría, alta/baja de
  usuarios, subida de ficheros, acceso a `/.env`, excepciones no controladas.
- `logs/app/sql.log` — **todas** las sentencias SQL (listener de SQLAlchemy).

Contexto añadido automáticamente: `ip`, `method`, `path`, `user_id`, `user_agent`.

---

## 3. Arquitectura física (despliegue)

Tres *stacks* de Docker Compose **separados** (proyectos y redes distintas),
acoplados solo por el **bind-mount de `./logs`**:

```
┌────────────────────────────── HOST (Linux) ──────────────────────────────┐
│                                                                            │
│  Stack APP  (docker-compose.yml)            Stack BLOG (docker/)            │
│  ┌─────────────┐   ┌──────────────┐         ┌────────────┐  ┌────────────┐ │
│  │   nginx     │──►│ web (gunicorn│         │  drupal    │─►│ drupal_db  │ │
│  │ :8000 → :80 │   │  Flask :8000)│         │ PHP5.6+7.30│  │ MariaDB10.6│ │
│  └──────┬──────┘   └──────┬───────┘         │  :8080→:80 │  └─────┬──────┘ │
│         │ access/error    │ app+sql         └─────┬──────┘        │general │
│         ▼                 ▼                       ▼ apache         ▼ +error │
│  ───────────────────────  ./logs/  ───────────────────────────────────────│
│   logs/nginx  logs/app   logs/drupal/apache   logs/drupal/mariadb          │
│                              │ (bind-mount :ro)                            │
│                              ▼                                              │
│  Stack SIEM (siem/)   ┌──────────────────────────────┐                     │
│                       │  wazuh.manager 4.9.2          │                     │
│                       │  localfiles → decoders+reglas │                     │
│                       │  → /var/ossec/.../alerts.json │                     │
│                       └──────────────────────────────┘                     │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Servicios / contenedores

| Stack | Servicio | Imagen | Puerto (host→cont) | Volúmenes |
|-------|----------|--------|--------------------|-----------|
| app | `nginx` | nginx:1.27-alpine | 8000→80 | `deploy/nginx/default.conf`, `logs/nginx` |
| app | `web` | `fakenv/web` (deploy/Dockerfile.web, gunicorn) | interno 8000 | repo en `/app` (código + `fakenv.db` + `logs`) |
| blog | `drupal` | `fakenv/drupal7.30` (Dockerfile.drupal) | 8080→80 | `drupal_data`, `logs/drupal/apache`, `apache-logs.conf` |
| blog | `drupal_db` | mariadb:10.6 | interno 3306 | `drupal_db_data`, `logs/drupal/mariadb` |
| siem | `wazuh.manager` | wazuh/wazuh-manager:4.9.2 | 1514/1515/55000 | `../logs` (ro), `ossec.conf`, `local_rules.xml`, `wazuh_alerts` |

> Desarrollo sin Docker: `python run.py` (servidor Werkzeug en `:5000`), que
> también escribe en `logs/app/`.

### 3.2 Persistencia (volúmenes)

- `fakenv.db` — SQLite de la app (en el host, compartido con el contenedor `web`).
- `drupal_db_data` — datos de MariaDB.
- `drupal_data` — `sites/default` de Drupal (`settings.php` + ficheros), sobrevive a reconstrucciones.
- `wazuh_alerts` — alarmas del SIEM (`alerts.json`).
- `./logs/` — logs centralizados (gitignored, generados en runtime).

### 3.3 Flujo de detección

1. Los servicios escriben logs en `./logs/`.
2. El Wazuh Manager los lee como `localfile` (JSON para la app, apache para
   web, mysql para MariaDB).
3. Decoders integrados + `siem/config/local_rules.xml` (IDs 100100–100130)
   generan **alarmas** en `alerts.json` (IDOR, fail-open de telemetría, acceso a
   fichero sensible, fuerza bruta, SQLi, alta/baja de admin…).

---

## 4. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Python 3.13, Flask 3, SQLAlchemy 2, gunicorn |
| Frontend | Jinja2, HTML/CSS/JS vanilla, SVG |
| BD app | SQLite (def.) / MySQL (opc.) |
| Blog | Drupal 7.30 + PHP 5.6 + MariaDB 10.6 |
| Proxy | nginx 1.27 |
| SIEM | Wazuh 4.9 |
| Infra | Docker / Docker Compose |

---

## 5. Estructura del repositorio

```
.
├── app/                  # paquete Flask (factory, blueprints, models, logging)
├── config.py  run.py  seed.py
├── deploy/               # Dockerfile.web (gunicorn) + nginx/
├── docker-compose.yml    # stack APP (web + nginx)
├── docker/               # stack BLOG (Drupal 7.30 + MariaDB)
├── siem/                 # stack SIEM (Wazuh manager + ossec.conf + reglas)
├── logs/                 # logs centralizados (runtime, gitignored)
├── docs/SIEM.md          # guía del SIEM
├── arquitectura.md       # este documento
└── README.md             # descripción + vulnerabilidades (OWASP)
```

Referencias: vulnerabilidades en `README.md` §1 · SIEM en `docs/SIEM.md`.
