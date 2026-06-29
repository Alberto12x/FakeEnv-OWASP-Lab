"""Autenticación: login, logout y recuperación de cuenta.

Debilidades buscadas (A07): el login no tiene rate limiting ni MFA, así que se
puede hacer fuerza bruta sin freno; y la recuperación se apoya en una sola
pregunta de seguridad cuya respuesta se guarda en claro y se compara sin
distinguir mayúsculas. El hash de la contraseña es MD5 (ver app/security.py).
"""

from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.blueprints.auth import auth_bp
from app.extensions import db
from app.logging_config import log_event
from app.models import User
from app.security import hash_password, verify_password


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        # Se admite indistintamente usuario o email como identificador.
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user and verify_password(password, user.password):
            session["user_id"] = user.id
            log_event("login_success", username=user.username, role=user.role)
            flash(f"Bienvenido de nuevo, {user.full_name}.", "success")
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("dashboard.index"))

        log_event("login_failed", level="warning", identifier=identifier)
        flash("Credenciales incorrectas.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    log_event("logout")
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Paso 1: localizar la cuenta y mostrar su pregunta de seguridad."""
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        if user is None:
            flash("No existe ninguna cuenta con ese identificador.", "error")
            return render_template("auth/forgot.html")

        return render_template("auth/forgot_question.html", user=user)

    return render_template("auth/forgot.html")


@auth_bp.route("/forgot/reset", methods=["POST"])
def forgot_reset():
    """Paso 2: validar la respuesta de seguridad y fijar la nueva contraseña."""
    username = request.form.get("username", "").strip()
    answer = request.form.get("answer", "").strip()
    new_password = request.form.get("new_password", "")

    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Cuenta no encontrada.", "error")
        return redirect(url_for("auth.forgot"))

    # Verificación débil: la respuesta se guarda en claro y se compara sin
    # distinguir mayúsculas, así que basta adivinar el dato (suele ser público).
    if user.security_answer.strip().lower() != answer.lower():
        log_event(
            "password_reset_failed", level="warning", username=user.username
        )
        flash("La respuesta de seguridad es incorrecta.", "error")
        return render_template("auth/forgot_question.html", user=user)

    if not new_password:
        flash("La nueva contraseña no puede estar vacía.", "error")
        return render_template("auth/forgot_question.html", user=user)

    user.password = hash_password(new_password)
    db.session.commit()
    log_event("password_reset_success", level="warning", username=user.username)
    flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
    return redirect(url_for("auth.login"))
