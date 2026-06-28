from datetime import datetime

from app.extensions import db


class Property(db.Model):
    """An inmueble (home, office, …) owned by a client and monitored by FakeEnv."""

    __tablename__ = "properties"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    alias = db.Column(db.String(80), nullable=False)  # e.g. "Vivienda habitual"
    address = db.Column(db.String(200), default="")
    city = db.Column(db.String(80), default="")
    property_type = db.Column(db.String(40), default="Vivienda")  # Vivienda | Oficina | Local
    size_m2 = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    readings = db.relationship(
        "Telemetry", backref="property", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Property {self.alias} ({self.city})>"
