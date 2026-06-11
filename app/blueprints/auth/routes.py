"""Authentication routes.

INTENTIONAL WEAKNESSES (educational OWASP project):
  * No rate limiting and no MFA on login (OWASP A07 - Authentication Failures),
    enabling unrestricted credential brute-forcing.
  * Account recovery relies on a single security question whose answer is stored
    in plain text and compared case-insensitively.
  * Passwords are hashed with salted MD5 (see app/security.py).
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
from app.models import User
from app.security import hash_password, verify_password


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        # Accept either username or email as the identifier.
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier)
        ).first()

        # No rate limiting, no lockout, no MFA — by design.
        if user and verify_password(password, user.password):
            session["user_id"] = user.id
            flash(f"Bienvenido de nuevo, {user.full_name}.", "success")
            if user.is_admin:
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("dashboard.index"))

        flash("Credenciales incorrectas.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for("main.index"))


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    """Step 1: identify the account and reveal its security question."""
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
    """Step 2: verify the security answer and set a new password."""
    username = request.form.get("username", "").strip()
    answer = request.form.get("answer", "").strip()
    new_password = request.form.get("new_password", "")

    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Cuenta no encontrada.", "error")
        return redirect(url_for("auth.forgot"))

    # Weak verification: plain-text, case-insensitive comparison.
    if user.security_answer.strip().lower() != answer.lower():
        flash("La respuesta de seguridad es incorrecta.", "error")
        return render_template("auth/forgot_question.html", user=user)

    if not new_password:
        flash("La nueva contraseña no puede estar vacía.", "error")
        return render_template("auth/forgot_question.html", user=user)

    user.password = hash_password(new_password)
    db.session.commit()
    flash("Contraseña actualizada. Ya puedes iniciar sesión.", "success")
    return redirect(url_for("auth.login"))
