import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database. Defaults to a local SQLite file so the app runs out-of-the-box.
    # To use MySQL instead, set DATABASE_URL in .env, e.g.:
    #   mysql+pymysql://fakenv_user:fakenv_pass@localhost:3306/fakenv_db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "fakenv.db"),
    )

    # ─── INTENTIONALLY INSECURE (educational / OWASP TFM) ───────────────────────
    # Single global salt for MD5 password hashing, read from the environment.
    # This is deliberately weak (no per-user salt, broken hash) to demonstrate
    # OWASP A02:2021 - Cryptographic Failures. DO NOT use in real systems.
    PASSWORD_SALT = os.environ.get("PASSWORD_SALT", "fakenv-static-salt")

    # Raw filesystem location for user-uploaded profile pictures.
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "app", "static", "uploads", "profiles")

    # External Drupal 7 blog (served by docker-compose, see docker/).
    BLOG_URL = os.environ.get("BLOG_URL", "http://localhost:8080")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
