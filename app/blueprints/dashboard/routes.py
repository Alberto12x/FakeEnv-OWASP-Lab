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
    render_template_string,
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

        # VULNERABILIDAD SSTI: El desarrollador crea una alerta dinámica usando f-strings
        # en lugar de pasar la variable como contexto.
        alerta_personalizada = f"Perfil de {user.name} actualizado correctamente!"
        flash(render_template_string(alerta_personalizada), "success")
        
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
    desde = request.args.get("desde", "2000-01-01")
    hasta = request.args.get("hasta", "2100-01-01")

    # VULNERABILIDAD SQLi (OWASP A03): las fechas del filtro se concatenan tal cual
    # en el SQL, sin parametrizar. Un valor malicioso (p. ej.  2100-01-01' OR '1'='1)
    # rompe el WHERE —incluida la restricción t.user_id— y vuelca la telemetría de
    # TODOS los usuarios. La consulta se ejecuta cruda contra el driver.
    sql = (
        "SELECT u.username, t.metric, t.reading_date, t.value, t.unit "
        "FROM telemetry t JOIN users u ON u.id = t.user_id "
        f"WHERE t.user_id = {user.id} "
        f"AND t.reading_date >= '{desde}' "
        f"AND t.reading_date <= '{hasta}' "
        "ORDER BY t.reading_date DESC"
    )

    error = None
    rows = []
    try:
        rows = db.session.connection().exec_driver_sql(sql).fetchall()
    except Exception as exc:  # noqa: BLE001 — se muestra el error de SQL (info leak)
        error = str(exc)

    return render_template(
        "dashboard/telemetry.html",
        rows=rows,
        desde=desde,
        hasta=hasta,
        error=error,
        sql=sql,
    )


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


