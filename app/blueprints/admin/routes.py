"""Administrator dashboard routes.

The admin has full visibility over every account, invoice and reading on the
platform. Access is gated by the `admin_required` decorator (role check only).
"""

from flask import abort, render_template

from app.blueprints.admin import admin_bp
from app.auth_utils import admin_required
from app.models import Invoice, Telemetry, User


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


@admin_bp.route("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = User.query.get(user_id)
    if user is None:
        abort(404)
    return render_template("admin/user_detail.html", user=user)


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
