from flask import render_template

from app.blueprints.main import main_bp


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
