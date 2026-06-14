import os

from flask import Response, abort, render_template

from app.blueprints.main import main_bp
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


# ─── INTENTIONALLY INSECURE (educational / OWASP TFM) ───────────────────────────
# Catch-all that serves any file from the project root as plain text, imitating a
# web server whose document root is the whole project directory. This exposes
# sensitive files such as .env, config.py or seed.py and enables path traversal
# (OWASP A05:2021 - Security Misconfiguration / Sensitive Data Exposure). It only
# fires for paths that no other route matches (e.g. /.env, /config.py).
@main_bp.route("/<path:filename>")
def serve_root_file(filename):
    target = os.path.join(BASE_DIR, filename)
    if not os.path.isfile(target):
        abort(404)
    with open(target, "rb") as handle:
        data = handle.read()
    return Response(data, mimetype="text/plain")
