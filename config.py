import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # FLASK_DEBUG gobierna el modo: con 1 se activa el debugger de Werkzeug
    # (consola RCE incluida), de ahí que en producción deba ir a 0.
    DEBUG = _as_bool(os.environ.get("FLASK_DEBUG", "0"))

    SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-in-production")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    # Por defecto SQLite en un fichero local para que arranque sin configurar
    # nada. Para MySQL, exportar DATABASE_URL (mysql+pymysql://user:pass@host/db).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "fakenv.db"),
    )

    # Salt único y estático para el hash MD5 de contraseñas. Es el fallo A02
    # (Cryptographic Failures) que queremos mostrar; jamás en un sistema real.
    PASSWORD_SALT = os.environ.get("PASSWORD_SALT", "fakenv-static-salt")

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "profiles")

    BLOG_URL = os.environ.get("BLOG_URL", "http://localhost:8080")

    # Directorio de logs que ingiere el SIEM: fakenv.log (eventos de la app) y
    # sql.log (toda la actividad SQL de SQLAlchemy).
    LOG_DIR = os.environ.get("LOG_DIR", os.path.join(BASE_DIR, "logs"))
