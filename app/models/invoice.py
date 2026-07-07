from datetime import datetime

from app.extensions import db


class Invoice(db.Model):
    """Factura mensual de suministros emitida a un cliente."""

    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    invoice_number = db.Column(db.String(40), unique=True, nullable=False)
    concept = db.Column(db.String(200), default="Consumo de suministros")

    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    issue_date = db.Column(db.Date, default=datetime.utcnow)
    due_date = db.Column(db.Date, nullable=False)

    # Consumos facturados del periodo.
    electricity_kwh = db.Column(db.Float, default=0.0)
    water_m3 = db.Column(db.Float, default=0.0)
    amount = db.Column(db.Float, nullable=False, default=0.0)  # total en EUR

    status = db.Column(db.String(20), default="pending")  # "paid" | "pending"

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number} {self.amount}EUR>"
