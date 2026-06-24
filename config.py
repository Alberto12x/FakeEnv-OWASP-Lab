import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # Single source of truth for the environment: FLASK_DEBUG in the .env.
    #   FLASK_DEBUG=1 -> desarrollo (debug on)
    #   FLASK_DEBUG=0 -> producción (debug off)
    DEBUG = _as_bool(os.environ.get("FLASK_DEBUG", "0"))

    SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-in-production")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = DEBUG
    # Database. Defaults to a local SQLite file so the app runs out-of-the-box.
    # To use MySQL instead, set DATABASE_URL in .env, e.g.:
    #   mysql+pymysql://fakenv_user:fakenv_pass@localhost:3306/fakenv_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "fakenv.db"),
    )

    # ─── INTENTIONALLY INSECURE (educational / OWASP TFM) ───────────────────────
    # Single global salt for MD5 password hashing, read from the environment.
    # Demonstrates OWASP A02:2021 - Cryptographic Failures. Never use in real apps.
    PASSWORD_SALT = os.environ.get("PASSWORD_SALT", "fakenv-static-salt")

    # Raw filesystem location for user-uploaded profile pictures.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "profiles")

    # External Drupal 7 blog (served by docker-compose, see docker/).
    BLOG_URL = os.environ.get("BLOG_URL", "http://localhost:8080")
