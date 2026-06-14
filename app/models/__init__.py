"""SQLAlchemy models for FakeEnv.

Importing this package registers every model with SQLAlchemy's metadata, which
is required for `db.create_all()` and Flask-Migrate autogeneration to work.
"""

from app.models.user import User
from app.models.property import Property
from app.models.invoice import Invoice
from app.models.telemetry import Telemetry

__all__ = ["User", "Property", "Invoice", "Telemetry"]
