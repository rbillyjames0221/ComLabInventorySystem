"""Admin routes"""
from flask import Blueprint, render_template, request, session, redirect, url_for, jsonify
import sqlite3
from app.config import Config
from app.models.user import User
from app.utils.validators import validate_lab_exists
from app.utils.auth_decorators import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route("/admin")
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    
    edit_mode = request.args.get("edit", "0") == "1"
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM labs ORDER BY id ASC")
        labs = cur.fetchall()
    return render_template("admin_dashboard.html", labs=labs, edit_mode=edit_mode)


@admin_bp.route("/admin/users")
@admin_required
def admin_users():
    """View pending users"""
    
    pending_users = User.get_pending_users()
    return render_template("admin_users.html", pending_users=pending_users)


@admin_bp.route("/account-management")
@admin_required
def account_management():
    """Account management page"""
    
    account_type = request.args.get("type", "user")
    data = User.get_active_users(account_type)
    data = [dict(row) for row in data]
    
    return render_template("account_management.html", data=data, account_type=account_type)


@admin_bp.route("/delete/<account_type>/<int:user_id>", methods=["POST"])
@admin_required
def delete_account(account_type, user_id):
    """Delete an account"""
    
    try:
        User.delete(user_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error"}), 500


@admin_bp.route("/pending_accounts")
@admin_required
def pending_accounts():
    """Get pending accounts"""
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, username, name, grade, section, role, created_at FROM users WHERE status='pending' ORDER BY id DESC")
        pending = [dict(row) for row in cur.fetchall()]
    
    return jsonify(pending)


@admin_bp.route("/approve/<int:user_id>", methods=["POST"])
@admin_required
def approve_account(user_id):
    """Approve a pending account"""
    
    User.approve(user_id)
    return redirect(url_for("admin.account_management"))


@admin_bp.route("/reject/<int:user_id>", methods=["POST"])
@admin_required
def reject_account(user_id):
    """Reject a pending account"""
    
    User.reject(user_id)
    return redirect(url_for("admin.account_management"))


@admin_bp.route("/add_lab", methods=["POST"])
@admin_required
def add_lab():
    """Add a new lab"""
    
    data = request.get_json()
    lab_name = data.get("lab_name", "").strip()

    if lab_name == "":
        return jsonify({"message": "Lab name cannot be empty."}), 400

    if validate_lab_exists(lab_name):
        return jsonify({"message": "Lab already exists!"}), 400
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO labs (name) VALUES (?)", (lab_name,))
        conn.commit()
    return jsonify({"message": f"{lab_name} added successfully!"})


@admin_bp.route("/rename_lab", methods=["POST"])
@admin_required
def rename_lab():
    """Rename a lab"""
    
    data = request.get_json()
    lab_id = data.get("id")
    new_name = data.get("new_name").strip()

    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE labs SET name = ? WHERE id = ?", (new_name, lab_id))
        conn.commit()

    return jsonify({"message": "Lab renamed successfully!"})


@admin_bp.route("/remove_lab", methods=["POST"])
@admin_required
def remove_lab():
    """Remove a lab"""
    
    data = request.get_json()
    lab_id = data.get("id")

    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM labs WHERE id = ?", (lab_id,))
        cur.execute("DELETE FROM devices WHERE comlab_id = ?", (lab_id,))
        conn.commit()

    return jsonify({"message": "Lab removed successfully!"})


@admin_bp.route("/pending_accounts/count")
def pending_accounts_count():
    """Get count of pending accounts"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE status='pending'")
        count = cur.fetchone()[0]
    return jsonify({"count": count})


@admin_bp.route("/api/profile_edits_pending")
@admin_required
def api_profile_edits_pending():
    """Get pending profile edits"""
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, username, full_name, grade, section, email, contact, submitted_at FROM profile_edits_pending WHERE status='pending'")
        rows = cur.fetchall()
        data = [dict(zip(["id","username","full_name","grade","section","email","contact","submitted_at"], row)) for row in rows]
    return jsonify(data)


@admin_bp.route("/approve_edit/<int:edit_id>", methods=["POST"])
@admin_required
def approve_edit(edit_id):
    """Approve a profile edit"""
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username, full_name, grade, section, email, contact FROM profile_edits_pending WHERE id=?", (edit_id,))
        row = cur.fetchone()
        if row:
            username, full_name, grade, section, email, contact = row
            User.update_profile(username, full_name, grade, section, email, contact)
            cur.execute("UPDATE profile_edits_pending SET status='approved' WHERE id=?", (edit_id,))
            conn.commit()
    return redirect(url_for("admin.account_management"))


@admin_bp.route("/reject_edit/<int:edit_id>", methods=["POST"])
@admin_required
def reject_edit(edit_id):
    """Reject a profile edit"""
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE profile_edits_pending SET status='rejected' WHERE id=?", (edit_id,))
        conn.commit()
    return redirect(url_for("admin.account_management"))


@admin_bp.route("/api/profile_edits_pending/count")
def profile_edits_pending_count():
    """Get count of pending profile edits"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM profile_edits_pending WHERE status='pending'")
        count = cur.fetchone()[0]
    return jsonify({"count": count})


@admin_bp.route("/unregistered_devices")
@admin_required
def unregistered_devices():
    """View unregistered devices across all PCs"""
    
    return render_template("unregistered_devices.html")


@admin_bp.route("/api/unregistered_devices")
@admin_required
def api_unregistered_devices():
    """Get all unregistered devices across all PCs"""
    
    try:
        import platform
        if platform.system() != "Windows":
            return jsonify({
                "success": False,
                "error": "Not Windows",
                "message": "Device detection is only available on Windows.",
                "devices": []
            })
        
        from app.utils.device_detector import get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
        
        if not IS_WINDOWS or not WIN32_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Windows API not available",
                "message": "Windows SetupAPI access is not available.",
                "devices": []
            })
        
        # Get all registered peripherals
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Check if vendor_id and product_id columns exist
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            has_vendor_product = "vendor_id" in columns and "product_id" in columns
            
            if has_vendor_product:
                cur.execute("SELECT unique_id, assigned_pc, lab_id, vendor_id, product_id FROM peripherals WHERE unique_id IS NOT NULL AND unique_id != ''")
            else:
                cur.execute("SELECT unique_id, assigned_pc, lab_id FROM peripherals WHERE unique_id IS NOT NULL AND unique_id != ''")
            registered_peripherals = cur.fetchall()
            
            # Get all devices with their tags and lab info
            cur.execute("""
                SELECT d.tag, d.hostname, d.comlab_id, l.name as lab_name
                FROM devices d
                LEFT JOIN labs l ON d.comlab_id = l.id
            """)
            devices = cur.fetchall()
        
        # Create a map of registered unique IDs to their PC info
        registered_unique_ids = {}
        for row in registered_peripherals:
            try:
                unique_id = row["unique_id"] if row["unique_id"] else None
                if unique_id:
                    registered_unique_ids[unique_id] = {
                        "pc_tag": row["assigned_pc"],
                        "lab_id": row["lab_id"]
                    }
            except (KeyError, TypeError):
                continue
        
        # Create a set of registered vendor_id + product_id combinations
        # If a device model (same vendor/product) is already registered, don't show it as unregistered
        registered_vendor_product = set()
        if has_vendor_product:
            for row in registered_peripherals:
                try:
                    # sqlite3.Row objects are accessed like dictionaries, handle None values
                    vendor_id = row["vendor_id"] if row["vendor_id"] else ""
                    product_id = row["product_id"] if row["product_id"] else ""
                    if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                        registered_vendor_product.add(f"{vendor_id}_{product_id}")
                except (KeyError, TypeError):
                    continue
        
        # Create a map of PC tags to device info
        pc_info_map = {row["tag"]: {
            "hostname": row["hostname"],
            "lab_id": row["comlab_id"],
            "lab_name": row["lab_name"]
        } for row in devices}
        
        # Get currently connected devices
        current_devices = get_connected_devices()
        
        # Debug: Print detected devices
        print(f"DEBUG: Found {len(current_devices)} connected devices")
        print(f"DEBUG: Registered unique IDs: {len(registered_unique_ids)}")
        print(f"DEBUG: Registered vendor/product combinations: {len(registered_vendor_product)}")
        
        # Find unregistered devices
        unregistered_list = []
        for device in current_devices:
            unique_id = device.get("unique_id", "")
            vendor_id = device.get("vendor", "")
            product_id = device.get("product", "")
            
            # Debug: Print device info
            print(f"DEBUG: Checking device - unique_id: {unique_id}, vendor: {vendor_id}, product: {product_id}")
            
            # Skip if already registered by unique_id
            if unique_id and unique_id in registered_unique_ids:
                print(f"DEBUG: Skipping - already registered by unique_id")
                continue
            
            # Skip if already registered by vendor_id + product_id (same device model)
            # If a device model (same vendor/product) is already registered, don't show other instances
            # The unique_id includes instance info which can vary, but vendor/product identifies the model
            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                vendor_product_key = f"{vendor_id}_{product_id}"
                if vendor_product_key in registered_vendor_product:
                    print(f"DEBUG: Skipping - device model (vendor/product: {vendor_product_key}) already registered")
                    continue  # This device model is already registered, skip it
            
            # This device is connected but not registered
            print(f"DEBUG: Adding to unregistered list")
            unregistered_list.append({
                "unique_id": unique_id,
                "name": device.get("type", "Unknown Device"),
                "brand": device.get("name", "Unknown"),
                "vendor": vendor_id,
                "product": product_id,
                "serial_number": device.get("unique_id", ""),
                "status": "connected",
                "pc_tag": None,  # Will be determined when registering
                "lab_id": None,
                "lab_name": None
            })
        
        print(f"DEBUG: Total unregistered devices: {len(unregistered_list)}")
        
        return jsonify({
            "success": True,
            "devices": unregistered_list,
            "count": len(unregistered_list)
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error getting unregistered devices: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get unregistered devices: {str(e)}",
            "devices": []
        }), 500


@admin_bp.route("/api/register_unregistered_device", methods=["POST"])
@admin_required
def register_unregistered_device():
    """Register an unregistered device"""
    
    try:
        from app.models.peripheral import Peripheral
        
        data = request.get_json()
        pc_tag = data.get("pc_tag")
        lab_id = data.get("lab_id")
        name = data.get("name")
        brand = data.get("brand")
        unique_id = data.get("unique_id")
        serial_number = data.get("serial_number", unique_id)
        vendor_id = data.get("vendor", "")
        product_id = data.get("product", "")
        
        if not all([pc_tag, lab_id, name, brand, unique_id]):
            return jsonify({
                "success": False,
                "error": "Missing required fields"
            }), 400
        
        # Register the peripheral with vendor_id and product_id
        Peripheral.create(
            name=name,
            brand=brand,
            assigned_pc=pc_tag,
            lab_id=lab_id,
            unique_id=unique_id,
            serial_number=serial_number or unique_id,
            status="connected",
            remarks="Registered from unregistered devices list",
            vendor_id=vendor_id if vendor_id and vendor_id != "UNKNOWN" else None,
            product_id=product_id if product_id and product_id != "UNKNOWN" else None
        )
        
        return jsonify({
            "success": True,
            "message": "Device registered successfully"
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error registering device: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to register device: {str(e)}"
        }), 500


@admin_bp.route("/api/labs")
@admin_required
def api_labs():
    """Get all labs"""
    
    try:
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name FROM labs ORDER BY id ASC")
            labs = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
        
        return jsonify({
            "success": True,
            "labs": labs
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "labs": []
        }), 500


@admin_bp.route("/api/devices_by_lab")
@admin_required
def api_devices_by_lab():
    """Get all devices for a lab"""
    
    try:
        lab_id = request.args.get("lab_id", type=int)
        if not lab_id:
            return jsonify({
                "success": False,
                "error": "lab_id is required"
            }), 400
        
        from app.models.device import Device
        devices = Device.get_by_location(lab_id)
        devices_list = [dict(row) for row in devices]
        
        return jsonify({
            "success": True,
            "devices": devices_list
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "devices": []
        }), 500


@admin_bp.route("/api/create_account", methods=["POST"])
@admin_required
def create_account():
    """Create a new user or admin account"""
    
    data = request.get_json()
    username = data.get("username", "").strip()
    name = data.get("name", "").strip()
    password = data.get("password", "").strip()
    role = data.get("role", "user").strip().lower()
    grade = data.get("grade", "").strip() or None
    section = data.get("section", "").strip() or None
    
    # Validation
    if not username or not name or not password:
        return jsonify({"status": "error", "message": "Username, name, and password are required"}), 400
    
    if role not in ["user", "professor", "admin"]:
        return jsonify({"status": "error", "message": "Invalid role"}), 400
    
    # Check if username already exists
    existing_user = User.get_by_username(username)
    if existing_user:
        return jsonify({"status": "error", "message": "Username already exists"}), 400
    
    try:
        # Create account with active status (admin-created accounts are auto-approved)
        User.create(username, name, password, role, grade, section, status="active")
        return jsonify({"status": "success", "message": "Account created successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_bp.route("/api/update_account/<int:user_id>", methods=["POST"])
@admin_required
def update_account(user_id):
    """Update account information"""
    
    data = request.get_json()
    username = data.get("username", "").strip() or None
    name = data.get("name", "").strip() or None
    grade = data.get("grade", "").strip() or None
    section = data.get("section", "").strip() or None
    
    # Validation
    if username is None and name is None and grade is None and section is None:
        return jsonify({"status": "error", "message": "No fields to update"}), 400
    
    # Check if username already exists (if changing username)
    if username:
        existing_user = User.get_by_username(username)
        if existing_user:
            # Get current user to check if it's the same user
            current_user = User.get_by_id(user_id)
            if not current_user or current_user["username"] != username:
                return jsonify({"status": "error", "message": "Username already exists"}), 400
    
    try:
        User.update_account_info(user_id, username, name, grade, section)
        return jsonify({"status": "success", "message": "Account updated successfully"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@admin_bp.route("/api/reset_password/<int:user_id>", methods=["POST"])
@admin_required
def reset_password(user_id):
    """Reset user password (requires admin confirmation)"""
    
    data = request.get_json()
    new_password = data.get("new_password", "").strip()
    admin_password = data.get("admin_password", "").strip()
    
    # Validation
    if not new_password:
        return jsonify({"status": "error", "message": "New password is required"}), 400
    
    if len(new_password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters long"}), 400
    
    if not admin_password:
        return jsonify({"status": "error", "message": "Admin confirmation password is required"}), 400
    
    # Verify admin password
    admin_username = session.get("username")
    admin_user = User.get_by_username(admin_username)
    if not admin_user:
        return jsonify({"status": "error", "message": "Admin user not found"}), 404
    
    if not User.verify_password(admin_user[1], admin_password):  # admin_user[1] is the password hash
        return jsonify({"status": "error", "message": "Invalid admin password"}), 401
    
    # Get target user
    target_user = User.get_by_id(user_id)
    if not target_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    try:
        # Reset the password - Row objects can be accessed by column name
        username = target_user["username"]
        # Use reset_password_by_admin to set password_reset_required flag
        User.reset_password_by_admin(username, new_password, admin_username)
        return jsonify({
            "status": "success", 
            "message": "Password reset successfully. User will be prompted to change password on next login."
        })
    except Exception as e:
        import traceback
        print(f"Error resetting password: {e}")
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500


@admin_bp.route("/admin/settings")
@admin_required
def admin_settings():
    """Admin settings page"""
    from app.models.system_settings import SystemSettings
    
    settings = SystemSettings.get_all()
    settings_dict = {row['setting_key']: row['setting_value'] for row in settings}
    
    return render_template("admin_settings.html", settings=settings_dict)


@admin_bp.route("/api/settings", methods=["GET", "POST"])
@admin_required
def api_settings():
    """Get or update system settings"""
    from app.models.system_settings import SystemSettings
    from app.utils.audit_log import log_audit
    
    if request.method == "GET":
        settings = SystemSettings.get_all()
        settings_dict = {row['setting_key']: row['setting_value'] for row in settings}
        return jsonify({"success": True, "settings": settings_dict})
    
    # POST - Update settings
    data = request.get_json()
    setting_key = data.get("setting_key")
    setting_value = data.get("setting_value")
    description = data.get("description", "")
    updated_by = session.get("username", "unknown")
    
    if not setting_key:
        return jsonify({"success": False, "message": "setting_key is required"}), 400
    
    try:
        SystemSettings.set(setting_key, setting_value, description, updated_by)
        log_audit(updated_by, "update_setting", "system_settings", None, 
                 f"Updated {setting_key} to {setting_value}", request.remote_addr)
        return jsonify({"success": True, "message": "Setting updated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@admin_bp.route("/api/audit_logs")
@admin_required
def api_audit_logs():
    """Get audit logs"""
    from app.utils.audit_log import get_audit_logs
    
    user_id = request.args.get("user_id")
    action = request.args.get("action")
    limit = request.args.get("limit", 100, type=int)
    
    try:
        logs = get_audit_logs(user_id, action, limit)
        logs_list = [dict(row) for row in logs]
        return jsonify({"success": True, "logs": logs_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "logs": []}), 500