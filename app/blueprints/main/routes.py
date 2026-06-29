import os

from flask import Response, abort, render_template

from app.blueprints.main import main_bp
from app.logging_config import log_event
from config import BASE_DIR


@main_bp.route("/")
def index():
    return render_template("main/index.html")


@main_bp.route("/about")
def about():
    return render_template("main/about.html")


@main_bp.route("/services")
def services():
    return render_template("main/services.html")


@main_bp.route("/contact")
def contact():
    return render_template("main/contact.html")


# Catch-all que simula un servidor cuyo document root es la raíz del proyecto:
# devuelve cualquier fichero como texto plano. Reproduce una mala configuración
# (A05) que expone .env, config.py o seed.py y permite path traversal. Al ir el
# último, solo atiende rutas que ninguna otra vista ha reclamado (/.env, etc.).
@main_bp.route("/<path:filename>")
def serve_root_file(filename):
    target = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(target):
        abort(404)
    log_event("sensitive_file_access", level="warning", requested=filename)
    with open(target, "rb") as handle:
        data = handle.read()
    return Response(data, mimetype="text/plain")
