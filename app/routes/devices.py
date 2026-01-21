"""Device and inventory routes"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
import sqlite3
import time
import secrets
from datetime import datetime
from app.config import Config
from app.models.device import Device
from app.models.peripheral import Peripheral
from app.models.user import User
from app.utils.validators import validate_device_exists
from app.utils.helpers import get_hostname, get_current_timestamp, get_machine_guid
from app.utils.auth_decorators import user_required, login_required
from werkzeug.utils import secure_filename
import os
from PIL import Image
import io

devices_bp = Blueprint('devices', __name__)


@devices_bp.route("/register_device/<token>", methods=["GET", "POST"])
def register_device(token):
    """Register a new device"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM labs")
        comlabs = cur.fetchall()
        
        # Check if comlab_id column exists in device_tokens table
        cur.execute("PRAGMA table_info(device_tokens)")
        columns = [row[1] for row in cur.fetchall()]
        has_comlab_id = "comlab_id" in columns
        
        # Retrieve token info (including comlab_id if column exists)
        if has_comlab_id:
            cur.execute("SELECT id, used, comlab_id FROM device_tokens WHERE token = ?", (token,))
            row = cur.fetchone()
            token_id = row[0] if row else None
            token_used = row[1] if row else None
            prefill_comlab_id = row[2] if row else None
        else:
            cur.execute("SELECT id, used FROM device_tokens WHERE token = ?", (token,))
            row = cur.fetchone()
            token_id = row[0] if row else None
            token_used = row[1] if row else None
            prefill_comlab_id = None

        if not row:
            return "Invalid or expired link.", 400
        if token_used == 1:
            return "This link has already been used.", 400

        if request.method == "POST":
            tag = request.form["tag"]
            location = request.form["location"]
            comlab_id = int(location)
            
            # Get client-side device information (from browser fingerprinting)
            unique_id = request.form.get("device_unique_id", "").strip() or None
            mac_address = request.form.get("device_mac_address", "").strip() or None
            selected_hostname = request.form.get("selected_hostname", "").strip()
            machine_id = request.form.get("machine_id", "").strip() or None
            
            # Try to get full device info from client-side detection
            full_device_info_json = request.form.get("full_device_info", "").strip()
            full_device_info = None
            if full_device_info_json:
                try:
                    import json
                    full_device_info = json.loads(full_device_info_json)
                except:
                    pass
            
            # Determine hostname - prioritize client-side detection
            if full_device_info and full_device_info.get("hostname"):
                hostname = full_device_info.get("hostname")
            elif selected_hostname:
                hostname = selected_hostname
            else:
                # Fallback to server-side hostname (but this won't work for remote clients)
                hostname = get_hostname()
            
            # Determine IP address - use client-side if available
            if full_device_info and full_device_info.get("local_ip"):
                ip_addr = full_device_info.get("local_ip")
            else:
                # Fallback to request remote address (may be ngrok IP, not client IP)
                ip_addr = request.remote_addr
            
            # Generate unique_id from client-side fingerprint if not provided
            if not unique_id:
                if full_device_info:
                    # Use client-side fingerprinting to generate unique ID
                    from app.utils.client_device_detector import generate_device_fingerprint
                    try:
                        unique_id = generate_device_fingerprint(full_device_info)
                    except Exception as e:
                        print(f"Error generating fingerprint: {e}")
                        # Fallback: generate from available info
                        import uuid
                        fingerprint_string = f"{hostname}-{ip_addr}-{request.headers.get('User-Agent', '')}"
                        unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint_string))
                elif mac_address and mac_address != "Unknown":
                    # Fallback: generate from MAC if available
                    import uuid
                    unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{mac_address}-{hostname}"))
                else:
                    # Last resort: generate from hostname and IP
                    import uuid
                    fingerprint_string = f"{hostname}-{ip_addr}-{request.headers.get('User-Agent', '')}"
                    unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint_string))
            
            # Check if device already exists - PRIORITIZE unique_id check
            # This ensures each device is uniquely identified regardless of hostname/tag
            existing = None
            if unique_id:
                # Check by unique_id first (most reliable)
                existing = validate_device_exists(unique_id=unique_id)
            
            # Also check by tag and hostname as secondary checks
            if not existing:
                existing = validate_device_exists(tag=tag, hostname=hostname)
            
            if existing:
                return f"⚠️ Device already registered in ComLab {existing[0]}. Cannot register in another ComLab.", 400

            # Insert device
            Device.create(tag, location, hostname, ip_addr, comlab_id, unique_id, mac_address, machine_id)

            # If detected device data is provided, register it as a peripheral
            detected_device_type = request.form.get("detected_device_type", "").strip()
            detected_device_name = request.form.get("detected_device_name", "").strip()
            detected_vendor = request.form.get("detected_vendor", "").strip()
            detected_product = request.form.get("detected_product", "").strip()
            detected_unique_id = request.form.get("detected_unique_id", "").strip()

            if detected_device_type and detected_unique_id:
                try:
                    # Use device type as name, vendor ID as brand
                    peripheral_name = detected_device_type
                    peripheral_brand = f"VID_{detected_vendor}" if detected_vendor else "Unknown"
                    peripheral_unique_id = detected_unique_id
                    peripheral_serial = detected_unique_id  # Use unique_id as serial number
                    
                    # Check if peripheral with this unique_id already exists
                    conn.row_factory = sqlite3.Row
                    check_cur = conn.cursor()
                    check_cur.execute("""
                        SELECT id FROM peripherals 
                        WHERE unique_id = ? AND lab_id = ? AND assigned_pc = ?
                    """, (peripheral_unique_id, comlab_id, tag))
                    existing_peripheral = check_cur.fetchone()
                    
                    if not existing_peripheral:
                        Peripheral.create(
                            name=peripheral_name,
                            brand=peripheral_brand,
                            assigned_pc=tag,
                            lab_id=comlab_id,
                            unique_id=peripheral_unique_id,
                            serial_number=peripheral_serial,
                            status="CONNECTED",
                            remarks=f"Auto-detected during device registration. Device Name: {detected_device_name}"
                        )
                except Exception as e:
                    # Log error but don't fail device registration
                    print(f"Error registering detected peripheral: {e}")

            # Mark token as used
            conn.execute("UPDATE device_tokens SET used = 1 WHERE id = ?", (token_id,))
            conn.commit()

            return render_template("success.html", tag=tag, hostname=hostname, ip=ip_addr)

    machine_guid = get_machine_guid()
    return render_template("register_device.html", comlabs=comlabs, prefill_comlab_id=prefill_comlab_id, machine_guid=machine_guid)


@devices_bp.route("/generate_link", methods=["GET"])
def generate_link():
    """Generate device registration link"""
    try:
        token = secrets.token_urlsafe(16)
        created_at = get_current_timestamp()
        comlab_id = request.args.get("comlab_id", type=int)  # Optional comlab_id parameter

        with sqlite3.connect(Config.DB_FILE) as conn:
            # Check if comlab_id column exists, add it if not
            cur = conn.cursor()
            try:
                cur.execute("PRAGMA table_info(device_tokens)")
                columns = [row[1] for row in cur.fetchall()]
            except sqlite3.OperationalError as e:
                # Table might not exist, create it
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS device_tokens (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        token TEXT UNIQUE NOT NULL,
                        created_at TEXT NOT NULL,
                        comlab_id INTEGER
                    )
                """)
                conn.commit()
                columns = []

            if "comlab_id" not in columns:
                try:
                    conn.execute("ALTER TABLE device_tokens ADD COLUMN comlab_id INTEGER")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            # Insert token with comlab_id (can be None)
            try:
                conn.execute(
                    "INSERT INTO device_tokens (token, created_at, comlab_id) VALUES (?, ?, ?)",
                    (token, created_at, comlab_id)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Token collision (very rare), generate a new one
                token = secrets.token_urlsafe(16)
                conn.execute(
                    "INSERT INTO device_tokens (token, created_at, comlab_id) VALUES (?, ?, ?)",
                    (token, created_at, comlab_id)
                )
                conn.commit()

        link = url_for("devices.register_device", token=token, _external=True)
        return jsonify({"success": True, "link": link})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to generate registration link. Please try again."
        }), 500


# Route removed - devices table view is now integrated into inventory management
# Use /comlab/<int:lab_id>/inventory instead


@devices_bp.route("/comlab/<int:lab_id>/inventory")
@login_required
def comlab_inventory(lab_id):
    """View inventory for a lab"""
    logged_in_student = session.get("username")
    hostname = get_hostname()
    
    # Fetch devices
    device_rows = Device.get_by_location(lab_id)
    
    # Convert Row objects to dictionaries
    # Ensure devices is always a list, even if empty
    devices = []
    if device_rows:
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            for row in device_rows:
                # Convert Row to dict - Row objects support dict() conversion
                row_dict = dict(row)
                device_tag = row_dict.get("tag", "")
                device_hostname = row_dict.get("hostname", "")
                
                # Get student_name if device is in use
                cur.execute("SELECT student_name FROM active_sessions WHERE pc_tag = ? OR pc_tag = ?", 
                           (device_hostname, device_tag))
                session_row = cur.fetchone()
                student_name = session_row['student_name'] if session_row else None
                
                # Determine status
                status = "In Use" if student_name else "Available"
                
                # Get IP address (handle both ip_address and ip_addres)
                ip_address = row_dict.get("ip_address") or row_dict.get("ip_addres")
                
                devices.append({
                    "tag": device_tag,
                    "id": row_dict.get("id"),
                    "hostname": device_hostname,
                    "mac_address": row_dict.get("mac_address"),
                    "unique_id": row_dict.get("unique_id"),
                    "ip_address": ip_address,
                    "student_name": student_name,
                    "status": status
                })

    # Fetch peripherals
    peripherals = Peripheral.get_by_lab(lab_id)
    peripherals_by_pc = {}
    
    for row in peripherals:
        # Convert Row to dict for easier access
        row_dict = dict(row)
        assigned_pc = row_dict.get("assigned_pc", "")
        
        if assigned_pc not in peripherals_by_pc:
            peripherals_by_pc[assigned_pc] = []
        
        peripherals_by_pc[assigned_pc].append({
            "id": row_dict.get("id"),
            "name": row_dict.get("name", ""),
            "brand": row_dict.get("brand", ""),
            "unique_id": row_dict.get("unique_id", ""),
            "serial_number": row_dict.get("serial_number", ""),
            "status": row_dict.get("status", ""),
            "remarks": row_dict.get("remarks", ""),
            "vendor_id": row_dict.get("vendor_id"),
            "product_id": row_dict.get("product_id")
        })

    # Attach peripherals to devices
    for d in devices:
        tag = d.get("tag", "")
        d["peripherals"] = peripherals_by_pc.get(tag, [])

    # Get lab name
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM labs WHERE id = ?", (lab_id,))
        lab_row = cur.fetchone()
        lab_name = lab_row[0] if lab_row else f"Lab {lab_id}"

    return render_template(
        "inventory.html",
        devices=devices,
        comlab_id=lab_id,
        lab_name=lab_name
    )


@devices_bp.route("/student_dashboard")
@user_required
def student_dashboard():
    """Student dashboard"""
    username = session.get("username")
    login_time = session.get("login_time", int(time.time()))
    hostname = get_hostname()

    student = User.get_profile(username)
    device_info = None
    peripherals = []
    lab_name = None

    with sqlite3.connect(Config.DB_FILE) as conn:
        # Set row_factory first before creating cursor
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("""
            UPDATE student_notifications SET is_read = 1
            WHERE student_id = ? AND is_read = 0
        """, (username,))
        conn.commit()

        # Get current device info from active_sessions
        cur.execute("SELECT pc_tag FROM active_sessions WHERE student_id = ?", (username,))
        session_row = cur.fetchone()
        pc_tag = session_row["pc_tag"] if session_row else hostname

        # Get device information
        # Check which IP column exists
        cur.execute("PRAGMA table_info(devices)")
        columns = [row[1] for row in cur.fetchall()]
        ip_column = "ip_addres" if "ip_addres" in columns else "ip_address"
        
        cur.execute(f"""
            SELECT d.id, d.tag, d.hostname, d.mac_address, d.unique_id, d.comlab_id, 
                   d.{ip_column} as ip_address, l.name as lab_name
            FROM devices d
            LEFT JOIN labs l ON d.comlab_id = l.id
            WHERE d.hostname = ? OR d.tag = ?
            LIMIT 1
        """, (pc_tag, pc_tag))
        device_row = cur.fetchone()
        
        if device_row:
            device_info = dict(device_row)
            lab_name = device_info.get("lab_name")
            comlab_id = device_info.get("comlab_id")
            device_tag = device_info.get("tag")  # Get the device tag (e.g., "PC BILLY")
            
            # Get peripherals assigned to this device
            # Use device tag instead of pc_tag, as peripherals are stored with assigned_pc = tag
            if comlab_id and device_tag:
                peripherals = Peripheral.get_by_pc(device_tag, comlab_id)
                # Convert Row objects to dictionaries, ensuring remarks are included
                peripherals_list = []
                for p in peripherals:
                    p_dict = dict(p)
                    # Ensure remarks field exists (handle None/empty cases)
                    if 'remarks' not in p_dict or p_dict['remarks'] is None:
                        p_dict['remarks'] = ''
                    peripherals_list.append(p_dict)
                peripherals = peripherals_list
                
                # Get registered unique IDs
                registered_unique_ids = {p.get("unique_id", "") for p in peripherals if p.get("unique_id")}
                
                # Auto-check and update peripheral status if on Windows
                # Also detect unregistered devices
                try:
                    import platform
                    if platform.system() == "Windows":
                        from app.utils.device_detector import get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
                        if IS_WINDOWS and WIN32_AVAILABLE:
                            # Get currently connected devices
                            current_devices = get_connected_devices()
                            current_unique_ids = {dev.get("unique_id", "") for dev in current_devices if dev.get("unique_id")}
                            
                            # Update status for each peripheral
                            for peripheral in peripherals:
                                unique_id = peripheral.get("unique_id", "")
                                current_status = peripheral.get("status", "").lower()
                                
                                if unique_id:
                                    if unique_id in current_unique_ids:
                                        # Device is connected
                                        if current_status != "connected":
                                            Peripheral.update_status_by_unique_id(unique_id, device_tag, "connected")
                                            peripheral["status"] = "connected"
                                    else:
                                        # Device is not connected
                                        if current_status == "connected":
                                            Peripheral.update_status_by_unique_id(unique_id, device_tag, "unplugged")
                                            peripheral["status"] = "unplugged"
                            
                            # Detect unregistered devices (connected but not in database)
                            for device in current_devices:
                                unique_id = device.get("unique_id", "")
                                if unique_id and unique_id not in registered_unique_ids:
                                    # Add unregistered device to peripherals list
                                    peripherals.append({
                                        "name": device.get("type", "Unknown Device"),
                                        "brand": device.get("name", "Unknown"),
                                        "serial_number": device.get("unique_id", ""),
                                        "unique_id": unique_id,
                                        "status": "connected",
                                        "remarks": "⚠️ UNREGISTERED DEVICE",
                                        "is_unregistered": True,
                                        "vendor": device.get("vendor", ""),
                                        "product": device.get("product", "")
                                    })
                except Exception as e:
                    # Silently fail if device detection is not available
                    print(f"Could not auto-update peripheral status: {e}")

        # Get anomalies
        cur.execute("""
            SELECT *
            FROM peripheral_alerts
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (username,))
        anomalies = cur.fetchall()

        # Check last emergency request status
        cur.execute("""
            SELECT status FROM emergency_logout_requests
            WHERE student_id = ?
            ORDER BY id DESC LIMIT 1
        """, (username,))
        req = cur.fetchone()

        if req:
            if req["status"] == "approved":
                flash("Your emergency logout request was approved!", "success")
            elif req["status"] == "declined":
                flash("Your emergency logout request was declined.", "error")

    return render_template(
        "student_dashboard.html",
        student=student,
        anomalies=anomalies,
        login_time=login_time,
        device_info=device_info,
        peripherals=peripherals,
        lab_name=lab_name,
    )


@devices_bp.route("/upload_profile", methods=["POST"])
@user_required
def upload_profile():
    """Upload profile picture"""
    if "profile_pic" not in request.files:
        flash("No file selected.", "error")
        return redirect("/student_dashboard")

    file = request.files["profile_pic"]
    if file.filename == "":
        flash("No selected file.", "error")
        return redirect("/student_dashboard")

    from app.utils.helpers import allowed_file
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(filepath)

        User.update_profile_picture(session["username"], filepath)
        flash("Profile picture updated!", "success")
    else:
        flash("Invalid file type.", "error")

    return redirect("/student_dashboard")


@devices_bp.route("/change_password", methods=["POST"])
@user_required
def change_password():
    """Change user password"""
    current_pw = request.form.get("current_password")
    new_pw = request.form.get("new_password")
    confirm_pw = request.form.get("confirm_password")

    if not current_pw or not new_pw or not confirm_pw:
        flash("Please fill all fields.", "error")
        return redirect("/student_dashboard")

    if new_pw != confirm_pw:
        flash("New passwords do not match.", "error")
        return redirect("/student_dashboard")

    user_data = User.get_by_username(session["username"])
    if user_data and User.verify_password(user_data[1], current_pw):
        User.update_password(session["username"], new_pw)
        flash("Password changed successfully!", "success")
    else:
        flash("Current password incorrect.", "error")

    return redirect("/student_dashboard")


@devices_bp.route("/edit_profile", methods=["POST"])
@user_required
def edit_profile():
    """Submit profile edit for admin approval"""
    submitted_at = get_current_timestamp()
    data = request.form
    
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO profile_edits_pending 
            (username, full_name, grade, section, email, contact, submitted_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session["username"], data["full_name"], data["grade"], data["section"], 
              data["email"], data["contact"], submitted_at, "pending"))
        conn.commit()

    flash("Profile edit request submitted for admin verification.", "success")
    return redirect("/student_dashboard")


@devices_bp.route("/upload_cropped_profile", methods=['POST'])
@user_required
def upload_cropped_profile():
    """Upload cropped profile picture"""
    user_id = session.get('username')
    img = request.files['croppedImage']

    try:
        # Open image via Pillow
        image = Image.open(io.BytesIO(img.read()))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")

        # Upload folder
        upload_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'profiles')
        os.makedirs(upload_folder, exist_ok=True)

        filename = f"profile_{user_id}.png"
        filepath = os.path.join(Config.UPLOAD_FOLDER, filename)
        image.save(filepath)

        # Update database
        User.update_profile_picture(user_id, '/static/uploads/' + filename)

        return jsonify({'success': True, 'image_url': '/static/uploads/' + filename})

    except Exception as e:
        print(f"Error saving image: {e}")
        return jsonify({'success': False, 'message': str(e)})


@devices_bp.route("/comlab/<int:comlab_id>/inventory/peripheral")
@login_required
def peripheral_summary(comlab_id):
    """View peripheral summary for a lab"""
    try:
        peripherals = Peripheral.get_by_lab(comlab_id)
        return render_template(
            "peripheral_summary.html",
            peripherals=peripherals,
            comlab_id=comlab_id
        )
    except Exception as e:
        return f"DB Error: {e}", 500


@devices_bp.route("/comlab/<int:comlab_id>/inventory/display_usb_devices")
@login_required
def display_usb_devices(comlab_id):
    """Display USB devices for a lab"""
    try:
        conn = sqlite3.connect(Config.DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT * FROM usb_devices WHERE location = ? ORDER BY timestamp DESC", (comlab_id,))
        devices = cur.fetchall()
        conn.close()

        devices_list = []
        column_names = [description[0] for description in cur.description]
        for device in devices:
            device_dict = dict(zip(column_names, device))
            devices_list.append(device_dict)

        return render_template("usb_devices.html", devices=devices_list, comlab_id=comlab_id)

    except sqlite3.Error as e:
        return f"<h1>Database Error:</h1><p>{str(e)}</p>", 500


@devices_bp.route("/comlab/<int:comlab_id>/inventory/view_alerts")
@login_required
def view_alerts(comlab_id):
    """View alerts for a lab"""
    try:
        from app.services.alert_service import AlertService
        alerts = AlertService.get_alerts_by_location(comlab_id)
        
        devices_list = []
        for alert in alerts:
            devices_list.append(dict(alert))

        return render_template("view_alerts.html", devices=devices_list, comlab_id=comlab_id)

    except sqlite3.Error as e:
        return f"<h1>Database Error:</h1><p>{str(e)}</p>", 500


@devices_bp.route("/comlab/<int:comlab_id>/inventory/summary")
@login_required
def summary(comlab_id):
    """View summary for a lab"""
    conn = sqlite3.connect(Config.DB_FILE)
    cur = conn.cursor()

    # Get filters
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    peripheral_type = request.args.get("peripheral_type")
    pc_no = request.args.get("pc_no")
    alert_type_filter = request.args.get("alert_type")

    # Base queries
    pc_query = "SELECT COUNT(*) FROM devices WHERE location=?"
    anomaly_query = "SELECT COUNT(*) FROM usb_devices WHERE location=?"
    alert_query = "SELECT COUNT(*) FROM peripheral_alerts WHERE location=?"

    pc_params = [comlab_id]
    anomaly_params = [comlab_id]
    alert_params = [comlab_id]

    # Apply filters
    if start_date and end_date:
        anomaly_query += " AND date(timestamp) BETWEEN ? AND ?"
        anomaly_params.extend([start_date, end_date])
        alert_query += " AND date(timestamp) BETWEEN ? AND ?"
        alert_params.extend([start_date, end_date])

    if pc_no:
        pc_query += " AND tag=?"
        pc_params.append(pc_no)
        anomaly_query += " AND device_name=?"
        anomaly_params.append(pc_no)
        alert_query += " AND device_name=?"
        alert_params.append(pc_no)

    if peripheral_type:
        anomaly_query += " AND device_type=?"
        anomaly_params.append(peripheral_type)
        alert_query += " AND device_type=?"
        alert_params.append(peripheral_type)

    if alert_type_filter:
        alert_query += " AND alert_type=?"
        alert_params.append(alert_type_filter.lower())

    # Execute queries
    cur.execute(pc_query, pc_params)
    pc_count = cur.fetchone()[0]

    cur.execute(anomaly_query, anomaly_params)
    anomaly_count = cur.fetchone()[0]

    # Peripherals breakdown
    all_types = ['Mouse','Keyboard','Monitor','Speaker','Webcam','FlashDrive','Hard Disk','Scanner','Printer']
    peripheral_counts = []

    for t in all_types:
        q = "SELECT COUNT(*) FROM peripherals WHERE lab_id=? AND name=?"
        params = [comlab_id, t]
        if pc_no:
            q += " AND assigned_pc=?"
            params.append(pc_no)
        if peripheral_type and peripheral_type.lower() != t.lower():
            peripheral_counts.append(0)
            continue
        cur.execute(q, params)
        peripheral_counts.append(cur.fetchone()[0])

    # Alerts breakdown
    alert_types = ['missing', 'faulty', 'replaced']
    alert_counts = {}
    for at in alert_types:
        if alert_type_filter and alert_type_filter.lower() != at:
            alert_counts[at] = 0
            continue

        q = "SELECT COUNT(*) FROM peripheral_alerts WHERE location=? AND alert_type=?"
        params = [comlab_id, at]
        if start_date and end_date:
            q += " AND date(timestamp) BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        if pc_no:
            q += " AND device_name=?"
            params.append(pc_no)
        if peripheral_type:
            q += " AND device_type=?"
            params.append(peripheral_type)
        cur.execute(q, params)
        alert_counts[at] = cur.fetchone()[0]

    alert_count = sum(alert_counts.values())
    conn.close()

    return render_template(
        "view_summary.html",
        comlab_id=comlab_id,
        pc_count=pc_count,
        peripheral_counts=peripheral_counts,
        anomaly_count=anomaly_count,
        alert_count=alert_count,
        alert_counts=alert_counts,
        types=all_types,
        request=request
    )


@devices_bp.route("/comlab/<int:lab_id>/devices")
@login_required
def comlab_devices(lab_id):
    """View devices for a lab - alias for inventory"""
    return redirect(url_for("devices.comlab_inventory", lab_id=lab_id))


@devices_bp.route("/comlab/<int:comlab_id>/inventory/view_summary")
@login_required
def view_summary_alias(comlab_id):
    """View summary for a lab - alias route"""
    return redirect(url_for("devices.summary", comlab_id=comlab_id))


@devices_bp.route("/comlab/<int:comlab_id>/inventory/peripheral_summary")
@login_required
def peripheral_summary_alias(comlab_id):
    """View peripheral summary - alias route"""
    return redirect(url_for("devices.peripheral_summary", comlab_id=comlab_id))


@devices_bp.route("/comlab/<int:comlab_id>/inventory/usb_devices")
@login_required
def usb_devices_alias(comlab_id):
    """View USB devices - alias route"""
    return redirect(url_for("devices.display_usb_devices", comlab_id=comlab_id))


@devices_bp.route("/comlab/<int:comlab_id>/inventory/view_reports")
@login_required
def view_reports(comlab_id):
    """View anomaly reports for a lab"""
    try:
        conn = sqlite3.connect(Config.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # Get lab name
        cur.execute("SELECT name FROM labs WHERE id=?", (comlab_id,))
        lab_row = cur.fetchone()
        lab_name = lab_row['name'] if lab_row else f"Lab {comlab_id}"
        
        # Get filters from query params
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        device_unit = request.args.get('device_unit', '')
        anomaly_type = request.args.get('anomaly_type', '')
        
        # Build query
        query = """
            SELECT ua.*, d.tag as device_tag
            FROM usb_devices ua
            LEFT JOIN devices d ON ua.device_name = d.tag OR ua.device_name = d.hostname
            WHERE ua.location = ?
        """
        params = [comlab_id]
        
        if start_date:
            query += " AND date(ua.timestamp) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(ua.timestamp) <= ?"
            params.append(end_date)
        if device_unit:
            query += " AND (ua.device_name = ? OR d.tag = ?)"
            params.extend([device_unit, device_unit])
        if anomaly_type:
            query += " AND ua.device_type = ?"
            params.append(anomaly_type)
        
        query += " ORDER BY ua.timestamp DESC"
        
        cur.execute(query, params)
        anomalies = cur.fetchall()
        
        # Get all devices for filter dropdown
        cur.execute("SELECT DISTINCT tag FROM devices WHERE location=? ORDER BY tag", (comlab_id,))
        devices = cur.fetchall()
        
        # Get anomaly types for filter
        cur.execute("SELECT DISTINCT device_type FROM usb_devices WHERE location=? ORDER BY device_type", (comlab_id,))
        anomaly_types = [row[0] for row in cur.fetchall()]
        
        conn.close()
        
        return render_template(
            "view_reports.html",
            anomalies=anomalies,
            comlab_id=comlab_id,
            lab_name=lab_name,
            devices=devices,
            anomaly_types=anomaly_types,
            request=request
        )
    except Exception as e:
        return f"Error: {str(e)}", 500


@devices_bp.route("/register_device")
@login_required
def register_device_page():
    """Register device page - shows form to generate link"""
    return render_template("register_device.html")
