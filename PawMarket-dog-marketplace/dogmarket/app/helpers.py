from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """Restrict a view to one or more roles (buyer / seller / admin)."""

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Please sign in to continue.", "info")
                return redirect(url_for("auth.login"))
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def get_or_404(model, ident, **kwargs):
    from .extensions import db

    obj = db.session.get(model, ident)
    if obj is None:
        abort(404)
    return obj
