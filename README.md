# FakeEnv — Aplicación web vulnerable (TFM / OWASP)

Web ficticia de una consultoría de ingeniería medioambiental que monitoriza la
telemetría del hogar (agua, electricidad, temperatura) y la facturación de
suministros. Construida con **Python 3 / Flask**, con un blog **Drupal 7.30** y
un **SIEM (Wazuh)** que recoge logs de todo y genera alarmas.

> ⚠️ **Software deliberadamente inseguro** (laboratorio educativo de TFM sobre el
> OWASP Top 10). No lo despliegues en Internet ni reutilices su código.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [Instalación y puesta en marcha](docs/instalacion.md) | Arranque con Docker o local, variables de entorno y credenciales de prueba |
| [Arquitectura](docs/arquitectura.md) | Arquitectura lógica y física (app, blog, SIEM) |
| [Vulnerabilidades (OWASP)](docs/vulnerabilidades.md) | Tabla de debilidades intencionadas y mapeo OWASP |
| [Blog Drupal 7.30](docs/blog-drupal.md) | Despliegue y explotación (Drupalgeddon2) |
| [SIEM (Wazuh)](docs/SIEM.md) | Recolección de logs, fuentes, reglas y alarmas |

## Arranque rápido (todo en Docker)

```bash
mkdir -p logs/app logs/nginx logs/drupal/apache logs/drupal/mariadb
chmod 777 logs/drupal/mariadb
docker compose run --rm web python seed.py     # BD de la app
docker compose up -d --build                   # app:8000 · blog:8080 · wazuh
```

Detalle completo en [docs/instalacion.md](docs/instalacion.md).

## Convenciones de desarrollo

- Ramas: `main` (estable) → `dev` (integración).
- Commits: Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`).
- Nunca se commitea `.env` ni la base de datos local.
