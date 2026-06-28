"""Administrator dashboard routes.

The admin has full visibility over every account, invoice and reading on the
platform. Access is gated by the `admin_required` decorator (role check only).
"""

from flask import abort, flash, redirect, render_template, request, url_for

from app.blueprints.admin import admin_bp
from app.auth_utils import admin_required, current_user
from app.constants import SECURITY_QUESTIONS
from app.extensions import db
from app.logging_config import log_event
from app.models import Invoice, Telemetry, User
from app.security import hash_password


@admin_bp.route("/")
@admin_required
def dashboard():
    stats = {
        "users": User.query.count(),
        "invoices": Invoice.query.count(),
        "pending_invoices": Invoice.query.filter_by(status="pending").count(),
        "readings": Telemetry.query.count(),
    }
    recent_invoices = (
        Invoice.query.order_by(Invoice.issue_date.desc()).limit(10).all()
    )
    return render_template(
        "admin/dashboard.html", stats=stats, recent_invoices=recent_invoices
    )


@admin_bp.route("/users")
@admin_required
def users():
    rows = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=rows)


@admin_bp.route("/users/new", methods=["GET", "POST"])
@admin_required
def user_new():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Usuario, email y contraseña son obligatorios.", "error")
            return render_template(
                "admin/user_form.html",
                form=request.form,
                security_questions=SECURITY_QUESTIONS,
            )

        # Reject duplicates on the unique columns to avoid a DB integrity error.
        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            flash("Ya existe un usuario con ese nombre o email.", "error")
            return render_template(
                "admin/user_form.html",
                form=request.form,
                security_questions=SECURITY_QUESTIONS,
            )

        user = User(
            username=username,
            email=email,
            password=hash_password(password),
            name=request.form.get("name", "").strip(),
            surname=request.form.get("surname", "").strip(),
            address=request.form.get("address", "").strip(),
            city=request.form.get("city", "").strip(),
            role="admin" if request.form.get("role") == "admin" else "user",
            security_question=request.form.get("security_question", "").strip(),
            security_answer=request.form.get("security_answer", "").strip(),
        )
        db.session.add(user)
        db.session.commit()
        log_event(
            "admin_user_created",
            level="warning",
            actor=current_user().username,
            new_user=user.username,
            new_role=user.role,
        )
        flash(f"Usuario «{user.username}» creado correctamente.", "success")
        return redirect(url_for("admin.users"))

    return render_template(
        "admin/user_form.html", form={}, security_questions=SECURITY_QUESTIONS
    )


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)
    return render_template("admin/user_detail.html", user=user)


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)

    # Don't let an admin delete the account they are currently logged in with.
    if current_user() and current_user().id == user.id:
        flash("No puedes eliminar tu propia cuenta de administrador.", "error")
        return redirect(url_for("admin.users"))

    log_event(
        "admin_user_deleted",
        level="warning",
        actor=current_user().username,
        deleted_user=user.username,
    )
    db.session.delete(user)  # cascades to invoices, telemetry and properties
    db.session.commit()
    flash(f"Usuario «{user.username}» eliminado.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/invoices")
@admin_required
def invoices():
    rows = Invoice.query.order_by(Invoice.issue_date.desc()).all()
    return render_template("admin/invoices.html", invoices=rows)


@admin_bp.route("/telemetry")
@admin_required
def telemetry():
    rows = (
        Telemetry.query.order_by(Telemetry.reading_date.desc()).limit(200).all()
    )
    return render_template("admin/telemetry.html", readings=rows)
