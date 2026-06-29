from app.extensions import db


class Telemetry(db.Model):
    """Lectura de un sensor del hogar para un día concreto.

    `metric` es uno de: "water" (m³), "electricity" (kWh), "temperature" (°C).
    """

    __tablename__ = "telemetry"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    property_id = db.Column(
        db.Integer, db.ForeignKey("properties.id"), nullable=True, index=True
    )

    reading_date = db.Column(db.Date, nullable=False, index=True)
    metric = db.Column(db.String(20), nullable=False, index=True)
    value = db.Column(db.Float, nullable=False, default=0.0)
    unit = db.Column(db.String(10), nullable=False, default="")

    def __repr__(self) -> str:
        return f"<Telemetry {self.metric}={self.value}{self.unit} {self.reading_date}>"
