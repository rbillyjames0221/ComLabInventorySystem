"""Authentication routes"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import logging
from datetime import datetime, timedelta
from app.config import Config
from app.models.user import User
from app.utils.validators import validate_username_exists
from app.utils.security import (
    record_login_attempt, get_failed_login_count, is_account_locked,
    lock_account, unlock_account, increment_failed_login_count,
    reset_failed_login_count, update_last_login
)
from app.services.device_monitor import start_monitoring
from app.utils.helpers import get_hostname, get_current_timestamp

auth_bp = Blueprint('auth', __name__)

# Initialize logger
logger = logging.getLogger(__name__)

# Rate limiter for login attempts - will be initialized in __init__.py
try:
    from app import limiter
except ImportError:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )


@auth_bp.route("/")
def home():
    """Home page - redirects to login"""
    # Redirect logged-in users to their dashboard
    if "username" in session:
        role = session.get("role")
        if role == "admin":
            return redirect("/admin")
        elif role in ["user", "professor"]:
            return redirect("/student_dashboard")
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new account"""
    if request.method == "POST":
        try:
            role = request.form.get("role")
            username = request.form.get("username")
            password = request.form.get("password")
            name = request.form.get("name")
            grade = None
            section = None

            # For students
            if role == "user":
                username = request.form.get("student_number")
                grade = request.form.get("grade")
                section = request.form.get("section")

            # For professors
            elif role == "professor":
                username = request.form.get("professor_id")

            # For admins
            elif role == "admin":
                username = request.form.get("username")
                name = request.form.get("name")

            # Input validation
            if not password or not username or not name:
                return jsonify({"success": False, "error": "Please fill all required fields!"})

            # Sanitize inputs
            username = username.strip()
            name = name.strip()
            password = password.strip()

            if len(username) < 3:
                return jsonify({"success": False, "error": "Username must be at least 3 characters!"})

            if len(password) < 8:
                return jsonify({"success": False, "error": "Password must be at least 8 characters!"})

            if validate_username_exists(username):
                return jsonify({"success": False, "error": "Username/ID already exists!"})

            User.create(username, name, password, role, grade, section, "pending")
            logger.info(f"New user registration: {username} ({role})")
            return jsonify({"success": True})

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({"success": False, "error": "An error occurred during registration. Please try again."})

    # GET request
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per 15 minutes")
def login():
    """Login page with security enhancements"""
    # Redirect logged-in users
    if "username" in session:
        role = session.get("role")
        if role == "admin":
            return redirect("/admin")
        elif role in ["user", "professor"]:
            return redirect("/student_dashboard")

    if request.method == "POST":
        try:
            # Fix KeyError vulnerability - use .get() instead of direct access
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            remember_me = request.form.get("remember_me") == "on"
            pc_tag = request.form.get("pc_tag") or request.args.get("pc_tag") or get_hostname()
            login_time = get_current_timestamp()
            ip_address = request.remote_addr or "unknown"

            # Input validation
            if not username or not password:
                flash("Please enter both username and password.", "error")
                record_login_attempt(username or "unknown", ip_address, success=False)
                return redirect("/login")

            # Check if account is locked
            locked, lock_until = is_account_locked(username)
            if locked:
                remaining_minutes = int((lock_until - datetime.now()).total_seconds() / 60)
                flash(f"Account is locked due to too many failed login attempts. Please try again in {remaining_minutes} minutes.", "error")
                record_login_attempt(username, ip_address, success=False)
                return redirect("/login")

            # Get user data
            user_data = User.get_by_username(username)

            if user_data:
                username_db, password_db, role, status, student_name = user_data

                # Check account status
                if status == "pending":
                    flash("Your account is pending. Please wait for admin approval.", "error")
                    record_login_attempt(username, ip_address, success=False)
                    logger.warning(f"Login attempt with pending account: {username} from {ip_address}")
                    return redirect("/login")

                # Verify password (constant-time comparison handled by werkzeug)
                if User.verify_password(password_db, password):
                    # Check if password reset is required
                    password_reset_required = User.check_password_reset_required(username_db)
                    
                    # Successful login
                    session["username"] = username_db
                    session["role"] = role
                    session["login_time"] = datetime.now().isoformat()
                    session["password_reset_required"] = password_reset_required
                    
                    if remember_me:
                        session["remember_me"] = True
                        session.permanent = True
                        # 30 days for remember me
                        session["session_timeout"] = (datetime.now() + timedelta(days=30)).isoformat()
                    else:
                        session["remember_me"] = False
                        # 8 hours for regular session
                        session["session_timeout"] = (datetime.now() + timedelta(hours=8)).isoformat()

                    # Reset failed login count and unlock account
                    reset_failed_login_count(username)
                    unlock_account(username)
                    update_last_login(username)
                    record_login_attempt(username, ip_address, success=True)
                    
                    logger.info(f"Successful login: {username} ({role}) from {ip_address}")
                    
                    # If password reset required, redirect to password change page
                    if password_reset_required:
                        flash("Please change your password before proceeding.", "warning")
                        return redirect("/change_password_first_login")

                    flash("Login successful!", "success")

                    # Start monitoring thread only for 'user' or 'professor' roles
                    if role in ["user", "professor"]:
                        start_monitoring(username_db)
                        
                        # Check if user is already logged in on a different PC
                        with sqlite3.connect(Config.DB_FILE) as conn:
                            cur = conn.cursor()
                            cur.execute("SELECT pc_tag FROM active_sessions WHERE student_id = ?", (username_db,))
                            existing_session = cur.fetchone()
                            
                            if existing_session and existing_session[0] != pc_tag:
                                # User is logging in from a different PC
                                old_pc_tag = existing_session[0]
                                flash(f"You were previously logged in on {old_pc_tag}. Session moved to {pc_tag}. Peripheral detection will only work on this PC.", "info")
                            
                            # Insert or replace into active_sessions (this will replace any existing session)
                            cur.execute("""
                                INSERT OR REPLACE INTO active_sessions (pc_tag, student_id, login_time, student_name)
                                VALUES (?, ?, ?, ?)
                            """, (pc_tag, username_db, login_time, student_name))
                            conn.commit()

                    # Redirect based on role
                    if role == "admin":
                        return redirect("/admin")
                    elif role in ["user", "professor"]:
                        return redirect("/student_dashboard")
                    else:
                        return redirect("/login")
                else:
                    # Failed password verification
                    failed_count = increment_failed_login_count(username)
                    record_login_attempt(username, ip_address, success=False)
                    logger.warning(f"Failed login attempt: {username} from {ip_address}")

                    # Lock account after 5 failed attempts
                    if failed_count >= 5:
                        lock_account(username, minutes=30)
                        flash("Account locked due to too many failed login attempts. Please try again in 30 minutes.", "error")
                    else:
                        remaining_attempts = 5 - failed_count
                        flash(f"Invalid username or password! {remaining_attempts} attempt(s) remaining.", "error")
            else:
                # User doesn't exist - still record attempt but don't reveal user existence
                record_login_attempt(username, ip_address, success=False)
                # Use generic error message to prevent username enumeration
                flash("Invalid username or password!", "error")

        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash("An error occurred during login. Please try again.", "error")
            if username:
                record_login_attempt(username, request.remote_addr or "unknown", success=False)

        return redirect("/login")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    """Logout admin"""
    username = session.get("username")
    session.clear()
    if username:
        logger.info(f"Admin logout: {username}")
    flash("Logged out successfully!", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/user/logout")
def user_logout():
    """Logout user - REMOVED time restriction"""
    logged_in_student = session.get("username")

    if logged_in_student:
        # Delete from active_sessions
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM active_sessions WHERE student_id = ?", (logged_in_student,))
            conn.commit()
        logger.info(f"User logout: {logged_in_student}")

    # Remove from Flask session
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change_password_first_login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def change_password_first_login():
    """Change password on first login after admin reset"""
    if "username" not in session:
        flash("Please login first.", "error")
        return redirect("/login")
    
    username = session.get("username")
    password_reset_required = session.get("password_reset_required", False)
    
    # Check if password reset is actually required
    if not password_reset_required and not User.check_password_reset_required(username):
        # Already changed password or not required
        return redirect("/student_dashboard" if session.get("role") in ["user", "professor"] else "/admin")
    
    if request.method == "POST":
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        if not new_password or not confirm_password:
            flash("Please fill all fields.", "error")
            return render_template("change_password_first_login.html")
        
        if new_password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("change_password_first_login.html")
        
        if len(new_password) < 8:
            flash("Password must be at least 8 characters long.", "error")
            return render_template("change_password_first_login.html")
        
        # Update password and clear reset flag
        User.update_password(username, new_password, clear_reset_flag=True)
        session["password_reset_required"] = False
        
        flash("Password changed successfully! You can now proceed to your dashboard.", "success")
        logger.info(f"Password changed on first login: {username}")
        
        # Redirect to appropriate dashboard
        role = session.get("role")
        if role == "admin":
            return redirect("/admin")
        elif role in ["user", "professor"]:
            return redirect("/student_dashboard")
        else:
            return redirect("/login")
    
    return render_template("change_password_first_login.html")
