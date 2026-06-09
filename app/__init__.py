from flask import Flask

from app.extensions import db, migrate
from config import config_map


def create_app(config_name: str = "development") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    _init_extensions(app)
    _register_blueprints(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.main import main_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
