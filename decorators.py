from functools import wraps
from flask import session, flash, redirect, url_for
from models import db, User


def login_required(f):
    """Redirect unauthenticated visitors to the login page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session presence; no DB query needed for this lightweight guard.
        if "user_id" not in session:
            flash("You must be logged in to access this page.", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Redirect non-admin users; require login first."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Two-step check: session presence, then admin flag from the DB.
        if "user_id" not in session:
            flash("You must be logged in to access this page.", "danger")
            return redirect(url_for('auth.login'))
        user = db.session.get(User, session["user_id"])
        if not user or not user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for('users.homepage'))
        return f(*args, **kwargs)
    return decorated_function
