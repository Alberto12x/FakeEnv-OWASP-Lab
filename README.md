# FakeEnv — Laboratorio vulnerable OWASP Top 10

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![Drupal](https://img.shields.io/badge/Drupal-7.30_(EOL)-0678BE?logo=drupal&logoColor=white)
![Wazuh](https://img.shields.io/badge/SIEM-Wazuh_4.9-3D7EFF)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-GPLv3-blue)

**FakeEnv** es un laboratorio de ciberseguridad desarrollado como **Trabajo Fin de
Máster (TFM)**. Simula la web de una consultoría de ingeniería medioambiental
que monitoriza la telemetría del hogar (agua, electricidad, temperatura) y la
facturación de suministros, y contiene **vulnerabilidades intencionadas** del
**OWASP Top 10**.

Sirve para practicar las dos caras de la seguridad:

- 🔴 **Red Team**: explotar IDOR, SSTI, subida de archivos sin control, *fail-open*,
  criptografía débil, desconfiguraciones y un Drupal desactualizado
  (*Drupalgeddon* / *Drupalgeddon2*).
- 🔵 **Blue Team**: detectar esos mismos ataques con un **SIEM Wazuh** que recoge los
  logs de todos los componentes y genera alertas con reglas personalizadas.

> [!CAUTION]
> **Software deliberadamente inseguro**, pensado solo para fines educativos.
> Ejecútalo únicamente en local o en una red aislada. **No lo despliegues en
> Internet ni reutilices su código en producción.** Por defecto, todos los
> puertos se publican solo en `127.0.0.1`.

---

## 🧱 Arquitectura

| Servicio | Tecnología | URL |
|----------|------------|-----|
| App FakeEnv | Flask + gunicorn tras nginx | <http://localhost:8000> |
| Blog | Drupal 7.30 + MariaDB | <http://localhost:8080> |
| SIEM | Wazuh manager + indexer + dashboard | <https://localhost> |

Todo se levanta con un **único `docker-compose.yml`** en la misma red. Detalle
de la arquitectura lógica y física en [docs/arquitectura.md](docs/arquitectura.md).

---

## 🐞 Vulnerabilidades incluidas

| Vulnerabilidad | Dónde | OWASP Top 10 (2021) |
|----------------|-------|---------------------|
| IDOR en facturas | `/dashboard/invoice?id_factura=` | A01 – Broken Access Control |
| *Fail-open* en filtro de telemetría | Telemetría | A01 – Broken Access Control |
| Hash MD5 con salt global | Contraseñas | A02 – Cryptographic Failures |
| SSTI (`render_template_string`) | Perfil | A03 – Injection |
| Subida de archivos sin validar + path traversal | Foto de perfil | A04 – Insecure Design |
| Ficheros del proyecto servibles (`/.env`, `/config.py`) | Raíz | A05 – Security Misconfiguration |
| Depurador de Werkzeug (RCE) y gunicorn `--reload` | Despliegue | A05 – Security Misconfiguration |
| Drupal 7.30 (Drupalgeddon SQLi, Drupalgeddon2 RCE) | Blog | A06 – Vulnerable & Outdated Components |
| Login sin rate limiting ni MFA, recuperación débil | Autenticación | A07 – Identification & Authentication Failures |

Tabla completa y demostraciones en [docs/vulnerabilidades.md](docs/vulnerabilidades.md).

---

## 🚀 Arranque rápido

Requisitos: **Docker** con **Docker Compose v2** y unos **4 GB de RAM libres**
(el indexer de Wazuh es el que más consume).

```bash
git clone https://github.com/Alberto12x/FakeEnv-OWASP-Lab.git
cd FakeEnv-OWASP-Lab
./run.sh
```

`run.sh` crea las carpetas de logs, puebla la base de datos de la app, levanta
todo el stack y carga el contenido del blog. Paso a paso (o sin Docker) en
[docs/instalacion.md](docs/instalacion.md).

> [!NOTE]
> Wazuh necesita `vm.max_map_count` ≥ 262144 en el host:
> `sudo sysctl -w vm.max_map_count=262144`

### 🔑 Credenciales de prueba

| Servicio | Usuario | Contraseña |
|----------|---------|------------|
| App (admin) | `admin` | `admin` |
| App (usuario) | `ana.torres` | `ana` |
| Drupal | `admin` | `admin123` |
| Wazuh Dashboard | `admin` | `SecretPassword` |

Más usuarios en [docs/instalacion.md](docs/instalacion.md#datos-de-prueba-y-credenciales).

---

## 📚 Documentación

| Documento | Contenido |
|-----------|-----------|
| [Instalación](docs/instalacion.md) | Docker o local, variables de entorno, credenciales |
| [Arquitectura](docs/arquitectura.md) | Arquitectura lógica y física (app, blog, SIEM) |
| [Vulnerabilidades](docs/vulnerabilidades.md) | Debilidades intencionadas y su mapeo OWASP |
| [Blog Drupal 7.30](docs/blog-drupal.md) | Despliegue y explotación (Drupalgeddon2) |
| [SIEM (Wazuh)](docs/SIEM.md) | Fuentes de logs, reglas y alarmas |
| [Reglas de Wazuh](docs/wazuh-reglas.md) | Cheatsheet de las reglas personalizadas |
| [Análisis de código](docs/analisis-codigo.md) | SAST, DAST, SCA, secretos e IaC |

---

## 📁 Estructura

```text
app/          Aplicación Flask (blueprints, modelos, plantillas)
deploy/       Dockerfile de la app y configuración de nginx
docker/       Imagen de Drupal 7.30 y script de contenido del blog
siem/         Configuración de Wazuh (reglas, indexer, dashboard)
docs/         Documentación del TFM
run.sh        Arranque completo del laboratorio
seed.py       Datos de prueba
```

---

## ⚖️ Licencia y uso responsable

Distribuido bajo la licencia [GNU GPLv3](LICENSE).

Este proyecto existe para aprender a encontrar, explotar y detectar
vulnerabilidades en un entorno controlado. Usa estas técnicas solo contra
sistemas propios o con autorización expresa. Consulta también
[SECURITY.md](SECURITY.md).

---

Desarrollado por [Alberto Martín Oruña](https://github.com/Alberto12x) como
Trabajo Fin de Máster.
