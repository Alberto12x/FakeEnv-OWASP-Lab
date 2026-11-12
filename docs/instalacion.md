# Instalación y puesta en marcha

## Opción A — Stack completo en Docker (recomendada)

Un **único `docker-compose.yml`** levanta todo: app (gunicorn) tras nginx, blog
Drupal + MariaDB y el SIEM (Wazuh).

```bash
mkdir -p logs/app logs/nginx logs/drupal/apache logs/drupal/mariadb
chmod 777 logs/drupal/mariadb
docker compose run --rm web python seed.py     # BD de la app
docker compose up -d --build                   # app:8000 · blog:8080 · wazuh
docker compose exec drupal bash /seed/seed_blog.sh   # contenido del blog (1ª vez)
docker compose exec wazuh tail -f /var/ossec/logs/alerts/alerts.json
```

- App: <http://localhost:8000> · Blog: <http://localhost:8080>
- Dashboard Wazuh: <https://localhost> (admin / `SecretPassword`, certificado autofirmado).
- Los puertos se publican **solo en `127.0.0.1`**. Para atacar el laboratorio
  desde otra máquina (p. ej. una VM Kali en una red aislada), arranca con
  `BIND_ADDR=0.0.0.0 docker compose up -d`. **Nunca en una red pública.**
- Parar / arrancar: `docker compose stop` / `docker compose start`.
- Detalle del SIEM en [SIEM.md](SIEM.md), del blog en [blog-drupal.md](blog-drupal.md).

## Opción B — Desarrollo local (sin Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
python seed.py                       # crea fakenv.db con datos de prueba
python run.py                        # http://127.0.0.1:5000
```

La aplicación arranca **sin configuración** (`config.py` trae valores por defecto
y usa SQLite). Para personalizarla, crea un `.env` en la raíz:

```dotenv
SECRET_KEY=pon-aqui-una-clave-larga-y-aleatoria   # python -c "import secrets; print(secrets.token_hex(32))"
PASSWORD_SALT=s4l7_f4k3nv_2026
```

## Variables de entorno

| Variable       | Descripción                                          | Por defecto |
|----------------|------------------------------------------------------|-------------|
| `FLASK_DEBUG`  | `1` = desarrollo (debug on) / `0` = producción (debug off) | `0` |
| `SECRET_KEY`   | Clave de firma de sesiones                           | inseguro de ejemplo |
| `DATABASE_URL` | Cadena de conexión; vacío = SQLite local             | SQLite |
| `PASSWORD_SALT`| Salt global para el hash MD5 (**débil a propósito**) | `change-this-static-salt` |
| `BLOG_URL`     | URL del blog Drupal                                  | `http://localhost:8080` |
| `LOG_DIR`      | Carpeta de logs que ingiere el SIEM                  | `./logs` |

## Datos de prueba y credenciales

Tras `python seed.py` (o `docker compose run --rm web python seed.py`):

| Usuario        | Contraseña | Rol   |
|----------------|------------|-------|
| `admin`        | `admin`    | admin |
| `ana.torres`   | `ana`      | user  |
| `carlos.ruiz`  | `carlos`   | user  |
| `lucia.mendez` | `lucia`    | user  |
| `javier.gil`   | `javier`   | user  |
| `marta.sanz`   | `marta`    | user  |
