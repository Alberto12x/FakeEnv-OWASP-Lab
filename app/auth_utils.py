"""Session helpers and access-control decorators.

Authentication state is kept as a bare user id in the Flask session, and access
control is enforced only by these decorators on the view functions that opt in.
Note that the invoice lookup in the client dashboard deliberately does NOT use
them, which is what makes the IDOR demonstration possible.
"""

from functools import wraps

from flask import abort, flash, redirect, session, url_for
from werkzeug.exceptions import HTTPException

from app.models import User


def current_user():
    """Return the logged-in User, or None."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            if current_user() is None:
                flash("Debes iniciar sesión para acceder.", "error")
                return redirect(url_for("auth.login"))
        except HTTPException:
            raise
        except Exception:
            # VULN (fail-open): si la comprobación lanza una excepción inesperada
            # se concede el acceso en lugar de denegarlo. Forzando esa excepción
            # (p. ej. un user_id de sesión malformado) se salta la autenticación.
            pass
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        try:
            user = current_user()
            if user is None:
                return redirect(url_for("auth.login"))
            if not user.is_admin:
                abort(403)
        except HTTPException:
            # Deja pasar los flujos normales (redirect a login / 403).
            raise
        except Exception:
            # VULN (fail-open): una excepción inesperada concede acceso de admin.
            pass
        return view(*args, **kwargs)

    return wrapped
