import os
from dotenv import load_dotenv

load_dotenv()


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "changeme-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # MySQL connection string: mysql+pymysql://user:password@host/dbname
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://fakenv_user:fakenv_pass@localhost/fakenv_db",
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = True  # logs SQL queries to stdout


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
