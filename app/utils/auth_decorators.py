"""Authentication decorators for route protection"""
from functools import wraps
from flask import session, redirect, url_for, flash, request
from datetime import datetime, timedelta
from app.config import Config


def login_required(f):
    """Decorator to require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login"))
        if session.get("role") != "admin":
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    """Decorator to require user or professor role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            flash("Please log in to access this page.", "error")
            return redirect(url_for("auth.login"))
        role = session.get("role")
        if role not in ["user", "professor"]:
            flash("Access denied. User privileges required.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def check_session_timeout():
    """Check if session has timed out"""
    if "username" in session:
        # Check if session has a timeout timestamp
        if "session_timeout" in session:
            timeout = datetime.fromisoformat(session["session_timeout"])
            if datetime.now() > timeout:
                session.clear()
                return True
        # For "remember me" sessions, check permanent session lifetime
        elif session.get("remember_me"):
            # 30 days for remember me
            if "login_time" in session:
                login_time = datetime.fromisoformat(session["login_time"])
                if datetime.now() > login_time + timedelta(days=30):
                    session.clear()
                    return True
        else:
            # Regular session: 8 hours
            if "login_time" in session:
                login_time = datetime.fromisoformat(session["login_time"])
                if datetime.now() > login_time + timedelta(hours=8):
                    session.clear()
                    return True
    return False

