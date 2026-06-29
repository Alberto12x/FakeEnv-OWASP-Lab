"""Logging JSON centralizado de FakeEnv.

Escribe logs estructurados (un objeto JSON por línea) que ingiere el SIEM Wazuh:

  * logs/app/fakenv.log -> peticiones HTTP, autenticación, eventos de seguridad
                           y excepciones no controladas.
  * logs/app/sql.log    -> TODAS las sentencias SQL ejecutadas (vía SQLAlchemy),
                           que es como capturamos la actividad de la BD SQLite.

Desde cualquier punto se emite un evento con `log_event("nombre", clave=valor)`;
el formatter añade solo el contexto de la petición (ip, método, ruta, usuario).
"""

import datetime
import json
import logging
import os
import traceback
from logging.handlers import RotatingFileHandler

from flask import got_request_exception, has_request_context, request, session

APP_LOGGER = "fakenv"
SQL_LOGGER = "fakenv.sql"

_sql_listener_registered = False


class JsonFormatter(logging.Formatter):
    """Serializa cada registro como una única línea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
        }

        if has_request_context():
            data["ip"] = request.headers.get(
                "X-Forwarded-For", request.remote_addr
            )
            data["method"] = request.method
            data["path"] = request.path
            data["user_agent"] = request.headers.get("User-Agent", "")
            try:
                data["user_id"] = session.get("user_id")
            except Exception:
                data["user_id"] = None

        # Campos estructurados adjuntados vía `extra={"fakenv": {...}}`.
        fields = getattr(record, "fakenv", None)
        if isinstance(fields, dict):
            data.update(fields)
        else:
            data["message"] = record.getMessage()

        if record.exc_info:
            data["exception"] = "".join(traceback.format_exception(*record.exc_info))

        return json.dumps(data, ensure_ascii=False, default=str)


def _build_handler(path: str) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path, maxBytes=5_000_000, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(JsonFormatter())
    return handler


def configure_logging(app) -> None:
    log_dir = os.path.join(app.config["LOG_DIR"], "app")
    os.makedirs(log_dir, exist_ok=True)

    app_logger = logging.getLogger(APP_LOGGER)
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    if not app_logger.handlers:
        app_logger.addHandler(_build_handler(os.path.join(log_dir, "fakenv.log")))

    sql_logger = logging.getLogger(SQL_LOGGER)
    sql_logger.setLevel(logging.INFO)
    sql_logger.propagate = False
    if not sql_logger.handlers:
        sql_logger.addHandler(_build_handler(os.path.join(log_dir, "sql.log")))

    _register_sql_logging()
    _register_request_logging(app)
    _register_exception_logging(app)

    app_logger.info("app_start", extra={"fakenv": {"event": "app_start"}})


def _register_sql_logging() -> None:
    global _sql_listener_registered
    if _sql_listener_registered:
        return

    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "before_cursor_execute")
    def _on_sql(conn, cursor, statement, parameters, context, executemany):
        logging.getLogger(SQL_LOGGER).info(
            "sql_query",
            extra={
                "fakenv": {
                    "event": "sql_query",
                    "statement": " ".join(str(statement).split()),
                    "parameters": str(parameters)[:1000],
                }
            },
        )

    _sql_listener_registered = True


def _register_request_logging(app) -> None:
    @app.after_request
    def _log_request(response):
        # Se omiten los ficheros estáticos para no inundar el SIEM.
        if not request.path.startswith("/static/"):
            log_event(
                "http_request",
                status=response.status_code,
                args=request.args.to_dict(flat=True),
            )
        return response


def _register_exception_logging(app) -> None:
    def _on_exception(sender, exception, **extra):
        logging.getLogger(APP_LOGGER).error(
            "unhandled_exception",
            exc_info=exception,
            extra={
                "fakenv": {
                    "event": "unhandled_exception",
                    "error": str(exception),
                    "error_type": type(exception).__name__,
                }
            },
        )

    got_request_exception.connect(_on_exception, app)


def log_event(event: str, level: str = "info", **fields) -> None:
    """Emite un evento estructurado de seguridad/aplicación a fakenv.log."""
    payload = {"event": event}
    payload.update(fields)
    getattr(logging.getLogger(APP_LOGGER), level)(
        event, extra={"fakenv": payload}
    )
