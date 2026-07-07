"""Modelos SQLAlchemy de FakeEnv.

Importar este paquete registra todos los modelos en la metadata de SQLAlchemy,
necesario para que funcionen `db.create_all()` y la autogeneración de migraciones
de Flask-Migrate.
"""

from app.models.user import User
from app.models.property import Property
from app.models.invoice import Invoice
from app.models.telemetry import Telemetry

__all__ = ["User", "Property", "Invoice", "Telemetry"]
