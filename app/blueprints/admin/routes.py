from flask import render_template

from app.blueprints.admin import admin_bp


@admin_bp.route("/")
def dashboard():
    return render_template("admin/dashboard.html")


@admin_bp.route("/users")
def users():
    return render_template("admin/users.html")
