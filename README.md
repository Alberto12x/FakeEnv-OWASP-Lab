# FakeEnv — Aplicación web vulnerable (TFM / OWASP)

FakeEnv es la web de una empresa ficticia de ingeniería medioambiental que
monitoriza la telemetría del hogar (agua, electricidad, temperatura) y la
facturación de suministros. Está construida con **Python 3 / Flask** y un
subsistema de blog en **Drupal 7**.

> ## ⚠️ Aviso: aplicación deliberadamente insegura
> Este proyecto se ha desarrollado como **laboratorio educativo** para un Trabajo
> Fin de Máster sobre el **OWASP Top 10**. Contiene vulnerabilidades **a propósito**
> (hashing MD5, IDOR, subida de archivos sin validar, ausencia de rate limiting,
> Drupal 7 EOL…). **No la despliegues en Internet ni reutilices su código en
> producción.** Cada punto débil está marcado en el código con un comentario que
> empieza por `INTENTIONAL`/`INTENTIONALLY`.

---

## Tabla de contenidos

1. [Vulnerabilidades incluidas](#1-vulnerabilidades-incluidas)
2. [Arquitectura](#2-arquitectura)
3. [Estructura del proyecto](#3-estructura-del-proyecto)
4. [Puesta en marcha (aplicación Flask)](#4-puesta-en-marcha-aplicación-flask)
5. [Datos de prueba y credenciales](#5-datos-de-prueba-y-credenciales)
6. [Blog en Drupal 7 (Docker)](#6-blog-en-drupal-7-docker)
7. [Variables de entorno](#7-variables-de-entorno)

---

## 1. Vulnerabilidades incluidas

| Componente | Debilidad intencionada | OWASP Top 10 (2021) |
|------------|------------------------|----------------------|
| Login | Sin rate limiting ni MFA | A07 – Identification & Authentication Failures |
| Contraseñas | Hash **MD5** con salt global del `.env` | A02 – Cryptographic Failures |
| Recuperación de contraseña | Pregunta de seguridad, respuesta en texto plano | A07 |
| Facturas | Acceso por `?id_factura=` sin comprobar propietario (**IDOR**) | A01 – Broken Access Control |
| Telemetría | Filtro de fechas con excepción mal controlada (*fail-open*): una fecha inválida ignora el filtro `user_id` y vuelca la telemetría de todos los usuarios | A01 – Broken Access Control |
| Perfil (mensaje) | **SSTI** vía `render_template_string` sobre datos del usuario | A03 – Injection |
| Foto de perfil | Subida de archivos sin `secure_filename`, sin validar tipo/tamaño | A04 / unrestricted file upload |
| Raíz del proyecto | Cualquier archivo servible como texto (`/.env`, `/config.py`…) y path traversal | A05 – Security Misconfiguration |
| Modo debug | Con `FLASK_DEBUG=1`, cualquier excepción muestra el depurador de Werkzeug (código fuente + consola = RCE) | A05 – Security Misconfiguration |
| Blog | Drupal 7.30 (EOL): SQLi *Drupalgeddon* (SA-CORE-2014-005) y RCE *Drupalgeddon2* (CVE-2018-7600) | A06 – Vulnerable & Outdated Components / A03 – Injection |

---

## 2. Arquitectura

* **Application Factory** (`create_app()` en [app/__init__.py](app/__init__.py)): construye la
  app a partir de un perfil de configuración y conecta las extensiones.
* **Blueprints** independientes:
  * `main` (`/`) — web pública.
  * `auth` (`/login`, `/logout`, `/forgot`) — autenticación y recuperación.
  * `dashboard` (`/dashboard`) — panel del cliente (facturas, telemetría, perfil).
  * `admin` (`/admin`) — panel de administración con visibilidad total.
* **Extensiones** ([app/extensions.py](app/extensions.py)): Flask-SQLAlchemy y Flask-Migrate,
  inicializadas con el patrón `init_app`.
* **Base de datos**: SQLite por defecto (cero configuración); MySQL opcional vía
  `DATABASE_URL`.
* **Blog**: Drupal 7 + MariaDB en contenedores, independiente de la app Flask.

---

## 3. Estructura del proyecto

```
TFM-APP-VULNERABLE-OWASP/
├── app/
│   ├── __init__.py            # Application Factory
│   ├── extensions.py          # db, migrate
│   ├── security.py            # hashing MD5 (inseguro a propósito)
│   ├── auth_utils.py          # sesión + decoradores login_required/admin_required
│   ├── models/                # User, Invoice, Telemetry
│   ├── blueprints/
│   │   ├── main/  auth/  dashboard/  admin/
│   ├── templates/             # Jinja2 (público, auth, dashboard, admin)
│   └── static/                # CSS, JS, uploads/
├── docker/
│   ├── Dockerfile.drupal      # imagen PHP 5.6 + Drupal 7.30
│   ├── docker-compose.yml     # Drupal 7.30 + MariaDB
│   └── seed_blog.sh           # instala Drupal y crea el contenido del blog
├── config.py                  # configuración única (lee el entorno)
├── run.py                     # punto de entrada
├── seed.py                    # puebla la BD con datos realistas
├── requirements.txt
├── .env.example
└── README.md
```

---

## 4. Puesta en marcha (aplicación Flask)

### 4.1 Requisitos
* Python 3.11+
* (Opcional) Docker, sólo para el blog

### 4.2 Entorno virtual e instalación
```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.3 Variables de entorno (opcional)
La aplicación arranca **sin configuración**: `config.py` trae valores por defecto
y usa SQLite. Para personalizarla, crea un fichero `.env` en la raíz con las
variables de la [sección 7](#7-variables-de-entorno), por ejemplo:
```dotenv
SECRET_KEY=pon-aqui-una-clave-larga-y-aleatoria
PASSWORD_SALT=s4l7_f4k3nv_2026
```
Para generar un `SECRET_KEY` fuerte:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4.4 Poblar la base de datos
```bash
python seed.py
```
Esto crea `fakenv.db` con usuarios, facturas y 30 días de telemetría.

### 4.5 Arrancar
```bash
python run.py
# o bien:  flask --app run.py run --debug
```
La aplicación queda disponible en **http://127.0.0.1:5000**.

---

## 5. Datos de prueba y credenciales

Tras ejecutar `python seed.py`:

| Usuario        | Contraseña | Rol   |
|----------------|------------|-------|
| `admin`        | `admin`    | admin |
| `ana.torres`   | `ana`      | user  |
| `carlos.ruiz`  | `carlos`   | user  |
| `lucia.mendez` | `lucia`    | user  |
| `javier.gil`   | `javier`   | user  |
| `marta.sanz`   | `marta`    | user  |

**Demostración rápida del IDOR**: inicia sesión como `ana.torres` y visita
`http://127.0.0.1:5000/dashboard/invoice?id_factura=7`: verás una factura que
pertenece a `carlos.ruiz`, sin ninguna comprobación de propiedad.

---

## 6. Blog en Drupal 7 (Docker)

Se construye una imagen propia con **Drupal 7.30 sobre PHP 5.6**
([docker/Dockerfile.drupal](docker/Dockerfile.drupal)). Esa versión (anterior a
7.32 y a 7.58) es vulnerable a **Drupalgeddon** (SA-CORE-2014-005, SQLi) y a
**Drupalgeddon2** (CVE-2018-7600, RCE no autenticado). Por eso no se usa la
imagen oficial `drupal:7`, que trae la última versión sobre PHP 8 (donde 7.30 ni
siquiera arranca).

### Puesta en marcha

```bash
cd docker
docker compose up -d --build          # construye la imagen (1ª vez tarda 1-2 min)
# Espera a que Drupal arranque y siembra Drupal + el contenido del blog:
docker compose exec drupal bash /seed/seed_blog.sh
```
El script instala Drupal con drush (creando la BD, instalando el cliente MySQL y
silenciando el correo) y crea categorías, autores ficticios y artículos sobre
ahorro de agua, energía geotérmica, ventanas eficientes, etc. Al terminar imprime
la versión de Drupal y el número de artículos.

* Blog: **http://localhost:8080**
* Admin de Drupal: `admin` / `admin123`
* El botón **Blog** de la web pública apunta a esta instancia (`BLOG_URL`).

La instalación (`settings.php` y ficheros) se guarda en el volumen `drupal_data`,
así que **sobrevive** a reconstrucciones y reinicios. El `--build` y el seeding
**solo hacen falta la primera vez** (o si cambias el `Dockerfile.drupal`).

En el día a día, con la imagen ya construida y el contenido ya sembrado:

```bash
docker compose start     # arranca los contenedores existentes
docker compose stop      # los para (sin borrar nada)
# Si habías hecho `down` (borra contenedores, no los volúmenes):
docker compose up -d     # los recrea reusando imagen y datos (sin --build)
```

Para empezar de cero (otra versión, instalación limpia) hay que borrar los
volúmenes y volver a construir + sembrar:

```bash
docker compose down -v && docker compose up -d --build
docker compose exec drupal bash /seed/seed_blog.sh
```

### Comprobar la versión

Desde el navegador, `http://localhost:8080/CHANGELOG.txt` (la 1ª línea es
`Drupal 7.30, …`), o por terminal: `docker compose exec drupal drush status`.

### Explotación (Drupalgeddon2)

La RCE se demostró con Metasploit (`exploit/unix/webapp/drupal_drupalgeddon2`):
`RHOSTS 127.0.0.1`, `RPORT 8080`, `TARGETURI /`, `PHP_FUNC passthru` → sesión
Meterpreter como `www-data` dentro del contenedor.

---

## 7. Variables de entorno

| Variable       | Descripción                                          | Por defecto |
|----------------|------------------------------------------------------|-------------|
| `FLASK_DEBUG`  | `1` = desarrollo (debug on) / `0` = producción (debug off) | `0` |
| `SECRET_KEY`   | Clave de firma de sesiones                           | inseguro de ejemplo |
| `DATABASE_URL` | Cadena de conexión; vacío = SQLite local             | SQLite |
| `PASSWORD_SALT`| Salt global para el hash MD5 (**débil a propósito**) | `change-this-static-salt` |
| `BLOG_URL`     | URL del blog Drupal                                  | `http://localhost:8080` |
| `LOG_DIR`      | Carpeta de logs que ingiere el SIEM                  | `./logs` |

---

## 8. SIEM (Wazuh) — recolección de logs y alarmas

Todos los componentes escriben logs en `./logs/` y un **Wazuh Manager** los
ingiere y genera alarmas. La app va detrás de **nginx + gunicorn**
(`docker compose up -d --build` → http://localhost:8000) y Wazuh se levanta con
`cd siem && docker compose up -d`. Detalle completo, fuentes y cómo ver las
alarmas en **[docs/SIEM.md](docs/SIEM.md)**.

---

## Convenciones de desarrollo
* Ramas: `main` (estable) → `dev` (integración).
* Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
* Nunca se commitea `.env` ni la base de datos local.
