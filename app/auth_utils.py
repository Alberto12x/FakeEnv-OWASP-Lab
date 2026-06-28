"""Session helpers and access-control decorators.

Authentication state is kept as a bare user id in the Flask session, and access
control is enforced only by these decorators on the view functions that opt in.
Note that the invoice lookup in the client dashboard deliberately does NOT use
them, which is what makes the IDOR demonstration possible.
"""

from functools import wraps

from flask import abort, flash, redirect, session, url_for

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
