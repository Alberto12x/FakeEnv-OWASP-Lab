import os

from flask import Flask

from app.extensions import db, migrate
from app.logging_config import configure_logging
from config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    configure_logging(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_context(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    migrate.init_app(app, db)
    # Importing the models package registers every table with SQLAlchemy.
    from app import models  # noqa: F401


def _register_blueprints(app: Flask) -> None:
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(admin_bp, url_prefix="/admin")


def _register_context(app: Flask) -> None:
    from app.auth_utils import current_user

    @app.context_processor
    def inject_globals():
        # Makes `current_user` and `blog_url` available in every Jinja template.
        return {
            "current_user": current_user(),
            "blog_url": app.config["BLOG_URL"],
        }
