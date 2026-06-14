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
| Foto de perfil | Subida de archivos sin `secure_filename`, sin validar tipo/tamaño | A04 / unrestricted file upload |
| Raíz del proyecto | Cualquier archivo servible como texto (`/.env`, `/config.py`…) y path traversal | A05 – Security Misconfiguration |
| Blog | Drupal 7 (EOL desde enero de 2025) | A06 – Vulnerable & Outdated Components |

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
│   ├── docker-compose.yml     # Drupal 7 + MariaDB
│   └── seed_blog.sh           # instala Drupal y crea el contenido del blog
├── config.py                  # configuración por clases
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

```bash
cd docker
docker compose up -d
# Espera ~30 s a que Drupal arranque y luego siembra el contenido:
docker compose exec drupal bash /seed_blog.sh
```
* Blog: **http://localhost:8080**
* Admin de Drupal: `admin` / `admin123`

El script instala Drupal con drush y crea categorías, autores ficticios y
artículos sobre ahorro de agua, energía geotérmica, ventanas eficientes, etc.
El botón **Blog** de la web pública apunta a esta instancia (`BLOG_URL`).

---

## 7. Variables de entorno

| Variable       | Descripción                                          | Por defecto |
|----------------|------------------------------------------------------|-------------|
| `FLASK_CONFIG` | Perfil (`development` / `production`)                | `development` |
| `SECRET_KEY`   | Clave de firma de sesiones                           | inseguro de ejemplo |
| `DATABASE_URL` | Cadena de conexión; vacío = SQLite local             | SQLite |
| `PASSWORD_SALT`| Salt global para el hash MD5 (**débil a propósito**) | `change-this-static-salt` |
| `BLOG_URL`     | URL del blog Drupal                                  | `http://localhost:8080` |

---

## Convenciones de desarrollo
* Ramas: `main` (estable) → `dev` (integración).
* Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
* Nunca se commitea `.env` ni la base de datos local.
