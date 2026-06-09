# FakEnv — Web Corporativa

Web corporativa de **FakEnv**, empresa ficticia de consultoría de ingeniería en medio ambiente. Construida con **Python 3.11+ / Flask 3** siguiendo patrones de diseño de nivel producción.

---

## Tabla de contenidos

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Arquitectura y decisiones de diseño](#2-arquitectura-y-decisiones-de-diseño)
3. [Estructura de carpetas](#3-estructura-de-carpetas)
4. [Guía de inicio rápido](#4-guía-de-inicio-rápido)
5. [Variables de entorno](#5-variables-de-entorno)
6. [Base de datos y migraciones](#6-base-de-datos-y-migraciones)
7. [Convenciones de desarrollo](#7-convenciones-de-desarrollo)

---

## 1. Descripción del proyecto

FakEnv ofrece servicios de auditoría ambiental, gestión de residuos y cálculo de huella de carbono. Esta aplicación sirve como:

- Página pública de presentación de servicios (`/`)
- Panel de administración interno (`/admin`)
- Base escalable para incorporar autenticación, modelos de datos y API REST en iteraciones futuras

---

## 2. Arquitectura y decisiones de diseño

### 2.1 Application Factory (`create_app()`)

Se adopta el patrón **Application Factory** definido en `app/__init__.py`. En lugar de crear la instancia de Flask en el módulo principal y usarla directamente, la factoría:

- Acepta un parámetro `config_name` (`"development"` | `"production"`) para construir aplicaciones con configuraciones distintas sin tocar código.
- Permite instanciar varias aplicaciones en el mismo proceso (imprescindible para tests de integración).
- Evita importaciones circulares: las extensiones se instancian en `extensions.py` sin contexto de app, y se vinculan a la app en `_init_extensions()` con el patrón `extension.init_app(app)`.

```
FLASK_CONFIG=production python run.py   # arranca en modo producción
```

### 2.2 Blueprints

El código de rutas y vistas se organiza en **Blueprints**, cada uno con su propio directorio de templates:

| Blueprint | Prefijo URL | Responsabilidad |
|-----------|-------------|-----------------|
| `main`    | `/`         | Páginas públicas: inicio, nosotros, servicios, contacto |
| `admin`   | `/admin`    | Panel interno: dashboard, gestión de usuarios |

Esta separación garantiza que añadir un nuevo módulo (p. ej. `api` en `/api/v1`) no requiere modificar el código existente: basta con crear un nuevo Blueprint y registrarlo en la factoría.

### 2.3 Preparación para MySQL (Flask-SQLAlchemy + Flask-Migrate)

Aunque no hay modelos definidos todavía, la integración con MySQL está lista desde el día 1:

- `app/extensions.py` instancia `SQLAlchemy()` y `Migrate()` **sin app** (patrón `init_app`).
- La cadena de conexión se lee de la variable de entorno `DATABASE_URL` en `config.py`, con un valor por defecto que usa el driver `PyMySQL` (`mysql+pymysql://...`).
- `Flask-Migrate` gestiona las migraciones Alembic. Cuando se añada el primer modelo bastará con ejecutar `flask db init && flask db migrate && flask db upgrade`.

### 2.4 Configuración basada en clases

`config.py` expone `DevelopmentConfig` y `ProductionConfig` que heredan de `BaseConfig`. El valor activo se selecciona a través de la variable de entorno `FLASK_CONFIG`, lo que permite cambiar el comportamiento sin tocar código.

---

## 3. Estructura de carpetas

```
TFM-APP-VULNERABLE-OWASP/
│
├── app/                            # Paquete principal de la aplicación
│   ├── __init__.py                 # Application Factory — create_app()
│   ├── extensions.py               # Instancias de extensiones (db, migrate)
│   │
│   ├── blueprints/
│   │   ├── main/                   # Blueprint público
│   │   │   ├── __init__.py
│   │   │   └── routes.py
│   │   └── admin/                  # Blueprint administrativo
│   │       ├── __init__.py
│   │       └── routes.py
│   │
│   ├── templates/
│   │   ├── base.html               # Layout base público
│   │   ├── main/                   # Templates del blueprint main
│   │   │   ├── index.html
│   │   │   ├── about.html
│   │   │   ├── services.html
│   │   │   └── contact.html
│   │   └── admin/                  # Templates del blueprint admin
│   │       ├── base_admin.html
│   │       ├── dashboard.html
│   │       └── users.html
│   │
│   └── static/
│       ├── css/
│       │   ├── main.css
│       │   └── admin.css
│       └── js/
│           └── main.js
│
├── config.py                       # Clases de configuración
├── run.py                          # Punto de entrada
├── requirements.txt
├── .env.example                    # Plantilla de variables de entorno
└── README.md
```

---

## 4. Guía de inicio rápido

### 4.1 Prerrequisitos

- Python 3.11 o superior
- MySQL 8.0+ (o MariaDB 10.6+) en ejecución local
- `git`

### 4.2 Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd TFM-APP-VULNERABLE-OWASP
```

### 4.3 Crear y activar el entorno virtual

```bash
# Crear el entorno virtual en la carpeta .venv
python3 -m venv .venv

# Activar (Linux / macOS)
source .venv/bin/activate

# Activar (Windows PowerShell)
.venv\Scripts\Activate.ps1
```

Cuando el entorno esté activo verás `(.venv)` al inicio del prompt.

### 4.4 Instalar dependencias

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4.5 Configurar las variables de entorno

Copia la plantilla y edítala con tus valores:

```bash
cp .env.example .env
```

Abre `.env` y ajusta como mínimo:

```dotenv
SECRET_KEY=genera-una-clave-segura-aqui
DATABASE_URL=mysql+pymysql://TU_USUARIO:TU_PASSWORD@localhost:3306/fakenv_db
```

Para generar una `SECRET_KEY` segura:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4.6 Crear la base de datos en MySQL

```sql
CREATE DATABASE fakenv_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'fakenv_user'@'localhost' IDENTIFIED BY 'fakenv_pass';
GRANT ALL PRIVILEGES ON fakenv_db.* TO 'fakenv_user'@'localhost';
FLUSH PRIVILEGES;
```

### 4.7 Ejecutar la aplicación en modo desarrollo

```bash
flask --app run.py run --debug
```

La aplicación estará disponible en **http://127.0.0.1:5000**

El panel de administración en **http://127.0.0.1:5000/admin**

---

## 5. Variables de entorno

| Variable        | Descripción                                   | Valor por defecto                          |
|-----------------|-----------------------------------------------|--------------------------------------------|
| `FLASK_APP`     | Módulo de entrada de Flask                    | `run.py`                                   |
| `FLASK_CONFIG`  | Perfil de configuración (`development`/`production`) | `development`                   |
| `FLASK_DEBUG`   | Activa el modo debug de Flask                 | `1`                                        |
| `SECRET_KEY`    | Clave para firmar sesiones y CSRF tokens      | `changeme-in-production` (**cambiar siempre**) |
| `DATABASE_URL`  | URI de conexión a MySQL vía PyMySQL           | `mysql+pymysql://fakenv_user:fakenv_pass@localhost/fakenv_db` |

---

## 6. Base de datos y migraciones

Una vez que se definan los modelos en `app/models/`, el flujo de migraciones es:

```bash
# Inicializar el directorio de migraciones (solo la primera vez)
flask db init

# Generar una migración a partir de los cambios en los modelos
flask db migrate -m "descripcion del cambio"

# Aplicar la migración a la base de datos
flask db upgrade

# Revertir la última migración (si es necesario)
flask db downgrade
```

---

## 7. Convenciones de desarrollo

- **Ramas**: `main` (producción) → `dev` (integración) → `feature/<nombre>` (trabajo)
- **Commits**: formato Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `chore:`)
- **Estilo**: PEP 8, 99 caracteres por línea
- **Nunca** commitear el archivo `.env` (ya incluido en `.gitignore`)
