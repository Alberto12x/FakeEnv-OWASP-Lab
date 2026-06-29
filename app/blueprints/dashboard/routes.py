import csv
import io
import os
from datetime import datetime

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
from app.logging_config import log_event
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
    # IDOR (A01): el id llega por query string y se resuelve tal cual. Falta el
    # único control que importa aquí —comprobar que la factura es del usuario—,
    # así que cambiando id_factura se leen las de cualquiera.
    id_factura = request.args.get("id_factura", type=int)
    if id_factura is None:
        abort(400, "Falta el parámetro id_factura")

    invoice = Invoice.query.get(id_factura)
    if invoice is None:
        abort(404)

    # Registramos el acceso cruzado para que el SIEM lo levante como alarma.
    me = current_user()
    if invoice.user_id != me.id:
        log_event(
            "idor_invoice_access",
            level="warning",
            id_factura=id_factura,
            owner=invoice.user.username,
            accessed_by=me.username,
        )

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

        # Subida sin red de seguridad (A04): nos fiamos del nombre original del
        # cliente —sin secure_filename ni validar tipo/tamaño—, de modo que se
        # admite cualquier extensión y el nombre puede salirse del directorio
        # con un "../../" (path traversal).
        file = request.files.get("profile_picture")
        if file and file.filename:
            filename = file.filename
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            file.save(save_path)
            user.profile_picture = filename
            log_event(
                "file_upload",
                username=user.username,
                filename=filename,
                content_type=file.mimetype,
            )

        db.session.commit()

        # SSTI (A03): se mete user.name dentro de la plantilla y se renderiza con
        # render_template_string. Como el nombre es editable por el usuario, un
        # valor tipo {{7*7}} se evalúa en Jinja en vez de mostrarse literal.
        alerta = f"Perfil de {user.name} actualizado correctamente!"
        flash(render_template_string(alerta), "success")

        return redirect(url_for("dashboard.profile"))

    return render_template("dashboard/profile.html", user=user)


def _build_series(rows, unit, color, width=560, height=150, pad=24):
    """Convierte una serie de lecturas (ascendente) en geometría SVG y resumen.

    Lo calculamos en el servidor para que la plantilla solo dibuje el <polyline>
    y el <polygon>, sin depender de ninguna librería de gráficas en JS.
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

    # Tendencia: media de la mitad reciente frente a la mitad antigua.
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
    # Rango por defecto amplísimo: sin filtrar, se ve todo el histórico propio.
    desde = request.args.get("desde", "01/01/2000")
    hasta = request.args.get("hasta", "31/12/2100")
    metrica = request.args.get("metrica", "")  # "" = todas

    query = Telemetry.query
    try:
        d1 = datetime.strptime(desde, "%d/%m/%Y").date()
        d2 = datetime.strptime(hasta, "%d/%m/%Y").date()
        # El filtro por user_id cuelga del mismo try que el parseo de fechas:
        # ese es el error de diseño que explotamos justo debajo.
        query = query.filter(
            Telemetry.user_id == user.id,
            Telemetry.reading_date >= d1,
            Telemetry.reading_date <= d2,
        )
    except Exception as exc:
        # Fail-open (A01): una fecha mal formada rompe el strptime antes de
        # aplicar NINGÚN filtro —tampoco el de usuario—, y la query acaba
        # devolviendo la telemetría de todos los usuarios en lugar de fallar.
        log_event(
            "telemetry_filter_bypass",
            level="warning",
            username=user.username,
            desde=desde,
            hasta=hasta,
            error=str(exc),
        )

    # El filtro de métrica sí es funcionalidad legítima y se aplica siempre.
    if metrica in ("water", "electricity", "temperature"):
        query = query.filter(Telemetry.metric == metrica)

    rows = query.order_by(Telemetry.reading_date.desc()).all()
    return render_template(
        "dashboard/telemetry.html",
        rows=rows,
        desde=desde,
        hasta=hasta,
        metrica=metrica,
    )


@dashboard_bp.route("/telemetry/export")
@login_required
def telemetry_export():
    user = current_user()
    metrica = request.args.get("metrica", "")

    rows_q = Telemetry.query.filter_by(user_id=user.id)
    if metrica in ("water", "electricity", "temperature"):
        rows_q = rows_q.filter_by(metric=metrica)
    rows = rows_q.order_by(Telemetry.reading_date.asc()).all()

    # CSV en memoria con la librería estándar; el export sí respeta el user_id.
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["fecha", "metrica", "valor", "unidad"])
    for r in rows:
        writer.writerow([r.reading_date.isoformat(), r.metric, r.value, r.unit])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=telemetria_{metrica or 'todas'}.csv"
        },
    )


