"""Sesión y control de acceso.

El estado de login es solo el id de usuario guardado en la sesión. El control
de acceso lo imponen estos decoradores allí donde se aplican: una vista que no
los lleve queda abierta. El detalle de factura del panel de cliente no comprueba
la propiedad del recurso a propósito, y de ahí sale el IDOR.
"""

from functools import wraps

from flask import abort, flash, redirect, session, url_for

from app.models import User


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return User.query.get(user_id)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Debes iniciar sesión para acceder.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("auth.login"))
        if not user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped
