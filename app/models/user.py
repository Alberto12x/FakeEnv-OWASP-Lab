from datetime import datetime

from app.extensions import db


class User(db.Model):
    """Cuenta de FakeEnv: cliente normal o administrador."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)

    # Digest hex MD5(salt + password). Débil a propósito — ver app/security.py.
    password = db.Column(db.String(32), nullable=False)

    name = db.Column(db.String(80), nullable=False, default="")
    surname = db.Column(db.String(80), nullable=False, default="")
    address = db.Column(db.String(200), default="")
    city = db.Column(db.String(80), default="")

    # Nombre del fichero del avatar (relativo a static/uploads/profiles), si hay.
    profile_picture = db.Column(db.String(255), nullable=True)

    # "user" o "admin". Determina el acceso al panel de administración.
    role = db.Column(db.String(20), nullable=False, default="user")

    # Pregunta de seguridad para recuperar la cuenta. La respuesta se guarda en
    # claro a propósito, para ilustrar un flujo de recuperación débil.
    security_question = db.Column(db.String(200), default="")
    security_answer = db.Column(db.String(200), default="")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship(
        "Invoice", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    readings = db.relationship(
        "Telemetry", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    properties = db.relationship(
        "Property", backref="owner", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}".strip() or self.username

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role})>"
