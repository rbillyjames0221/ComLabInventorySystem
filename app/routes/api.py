"""API routes"""
from flask import Blueprint, request, session, jsonify, Response
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sqlite3
import time
from datetime import datetime
from app.config import Config
from app.models.user import User
from app.models.device import Device
from app.models.peripheral import Peripheral
from app.services.alert_service import AlertService
from app.utils.helpers import get_hostname
from app.utils.auth_decorators import login_required, user_required

api_bp = Blueprint('api', __name__)

# Rate limiter will be initialized in __init__.py and passed here if needed
# For now, create a local limiter instance
try:
    from app import limiter
except ImportError:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"
    )


@api_bp.route("/api/logged_in_user")
def get_logged_in_user():
    """Get currently logged in user"""
    pc_tag = request.form.get("pc_tag") or request.args.get("pc_tag") or get_hostname()
    if not pc_tag:
        return jsonify({"error": "Missing pc_tag"}), 400

    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT student_name, student_id FROM active_sessions WHERE pc_tag=?", (pc_tag,))
        row = cur.fetchone()

        if row:
            student_name = row[0]
            student_id = row[1]

            # Get device_name from devices table
            device_data = Device.get_by_hostname(pc_tag)
            if device_data:
                tag, location = device_data
            else:
                tag, location = None, None

            return jsonify({
                "username": student_name,
                "user_id": student_id,
                "device_name": tag,
                "location": location
            })

        # Return empty JSON when no logged-in user
        return jsonify({
            "username": None,
            "user_id": None,
            "device_name": None,
            "location": None
        })


@api_bp.route("/api/usb_event", methods=['POST'])
@limiter.limit("10 per minute")
def usb_event():
    """Handle USB event"""
    data = request.get_json()
    result = AlertService.process_usb_event(data)
    
    if result.get("status") == "error":
        return jsonify(result), 500
    
    return jsonify(result), 200


@api_bp.route("/api/add_peripheral", methods=["POST"])
@user_required
@limiter.limit("20 per minute")
def api_add_peripheral():
    """Add a peripheral via API"""
    data = request.get_json()
    name = data.get("name")
    brand = data.get("brand")
    assigned_pc = data.get("pc_tag")
    lab_id = data.get("lab_id")
    unique_id = data.get("unique_id", "")
    serial_number = data.get("serial_number", "")
    vendor_id = data.get("vendor", "")
    product_id = data.get("product", "")
    status = "CONNECTED"

    if not name or not brand or not assigned_pc or not lab_id:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    peripheral_id = Peripheral.create(
        name, brand, assigned_pc, lab_id, unique_id, serial_number, status, "",
        vendor_id=vendor_id if vendor_id and vendor_id != "UNKNOWN" else None,
        product_id=product_id if product_id and product_id != "UNKNOWN" else None
    )

    return jsonify({
        "success": True,
        "peripheral": {
            "id": peripheral_id,
            "name": name,
            "brand": brand,
            "assigned_pc": assigned_pc,
            "unique_id": unique_id,
            "serial_number": serial_number,
            "status": status,
            "vendor_id": vendor_id if vendor_id and vendor_id != "UNKNOWN" else None,
            "product_id": product_id if product_id and product_id != "UNKNOWN" else None
        }
    })


@api_bp.route("/api/delete_peripheral", methods=["POST"])
@user_required
@limiter.limit("20 per minute")
def api_delete_peripheral():
    """Delete a peripheral via API"""
    data = request.get_json()
    pid = data.get("id")

    if not pid:
        return jsonify({"success": False, "message": "Missing peripheral ID"}), 400

    Peripheral.delete(pid)
    return jsonify({"success": True})


@api_bp.route("/api/edit_peripheral", methods=["POST"])
@user_required
@limiter.limit("20 per minute")
def api_edit_peripheral():
    """Edit a peripheral via API"""
    data = request.get_json()

    pid = data.get("id")
    name = data.get("name", "")
    brand = data.get("brand", "")
    serial = data.get("serial_number", "")
    unique_id = data.get("unique_id", "")
    remarks = data.get("remarks", "")
    
    if not pid:
        return jsonify({"success": False, "message": "Missing peripheral ID"}), 400

    try:
        # If only remarks is provided (other fields empty), update only remarks
        if name == '' and brand == '' and unique_id == '' and serial == '' and remarks is not None:
            Peripheral.update_remarks_by_id(pid, remarks)
        elif name and brand:
            # Update all fields (existing behavior for full edit)
            Peripheral.update(pid, name, brand, unique_id, serial, remarks)
        else:
            return jsonify({"success": False, "message": "Missing required fields"}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/comlab/<int:comlab_id>/add_peripheral", methods=["POST"])
@user_required
@limiter.limit("20 per minute")
def add_peripheral(comlab_id):
    """Add peripheral to a lab"""
    data = request.get_json()
    pc_tag = data.get("pc_tag")
    name = data.get("name")
    brand = data.get("brand")
    unique_id = data.get("unique_id")
    remarks = data.get("remarks")
    serial = data.get("serial_number")
    vendor_id = data.get("vendor", "")
    product_id = data.get("product", "")
    
    if not all([pc_tag, name, brand, serial]):
        return jsonify({"success": False, "message": "Missing fields"}), 400

    # Check if device exists
    device = Device.get_by_tag(pc_tag)
    if not device or str(device[2]) != str(comlab_id):
        return jsonify({"success": False, "message": f"PC '{pc_tag}' not found in this ComLab"}), 404

    # Check if peripheral already exists by name
    from app.utils.validators import validate_peripheral_exists
    if validate_peripheral_exists(pc_tag, name):
        return jsonify({"success": False, "message": f"{name} already exists for {pc_tag}"}), 400
    
    # Check if a device with the same vendor_id and product_id already exists on THIS PC
    # This prevents duplicate registration of the same device model on the same PC
    # but allows the same device model on different PCs
    if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
        # Check if vendor_id and product_id columns exist
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            
            if "vendor_id" in columns and "product_id" in columns:
                # Check for same vendor/product on the same PC
                cur.execute("""
                    SELECT id, name, brand 
                    FROM peripherals
                    WHERE vendor_id = ? AND product_id = ? AND assigned_pc = ?
                """, (vendor_id, product_id, pc_tag))
                existing = cur.fetchone()
                if existing:
                    # Same vendor/product on same PC - this is a duplicate
                    return jsonify({
                        "success": False,
                        "message": f"A device with Vendor ID {vendor_id} and Product ID {product_id} is already registered on {pc_tag} as '{existing[1]}' (Brand: {existing[2]})"
                    }), 400

    # Insert peripheral with status 'connected' when added by admin
    # Remarks can contain admin notes/manual entries
    remarks_value = remarks or ''
    peripheral_id = Peripheral.create(
        name, brand, pc_tag, str(comlab_id), unique_id, serial, 'connected', remarks_value,
        vendor_id=vendor_id if vendor_id and vendor_id != "UNKNOWN" else None,
        product_id=product_id if product_id and product_id != "UNKNOWN" else None
    )

    return jsonify({
        "success": True,
        "peripheral": {
            "id": peripheral_id,
            "name": name,
            "brand": brand,
            "unique_id": unique_id,
            "serial_number": serial,
            "status": 'connected',
            "remarks": remarks_value,
            "vendor_id": vendor_id if vendor_id and vendor_id != "UNKNOWN" else None,
            "product_id": product_id if product_id and product_id != "UNKNOWN" else None
        }
    })


@api_bp.route("/alerts/stream")
def alerts_stream():
    """Stream alerts via Server-Sent Events"""
    def event_stream():
        last_id = 0
        while True:
            with sqlite3.connect(Config.DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, serial_number, alert_type, location, timestamp
                    FROM peripheral_alerts
                    WHERE id > ? AND deleted = 0
                    ORDER BY id ASC
                """, (last_id,))
                rows = cur.fetchall()
                for row in rows:
                    last_id = row[0]
                    yield f"data: {row[3]}|{row[1]}|{row[2]}\n\n"  # location|serial_number|alert_type
            time.sleep(2)  # check every 2 seconds
    
    return Response(event_stream(), mimetype="text/event-stream")


@api_bp.route("/api/alerts/count")
def get_alerts_count():
    """Get count of active alerts for admin"""
    try:
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) 
                FROM peripheral_alerts 
                WHERE deleted = 0 
                AND alert_type IN ('faulty', 'missing', 'replaced')
            """)
            count = cur.fetchone()[0] or 0
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "count": 0}), 500


@api_bp.route("/api/alerts/list")
@api_bp.route("/alerts/list")  # Also support old route
def get_alerts_list():
    """Get list of active alerts for admin"""
    try:
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT 
                    a.id,
                    a.serial_number,
                    a.alert_type,
                    a.device_name,
                    a.device_type,
                    a.location as comlab_id,
                    a.timestamp,
                    l.name as lab_name
                FROM peripheral_alerts a
                LEFT JOIN labs l ON a.location = l.id
                WHERE a.deleted = 0 
                AND a.alert_type IN ('faulty', 'missing', 'replaced')
                ORDER BY a.timestamp DESC
                LIMIT 50
            """)
            rows = cur.fetchall()
            alerts = []
            for row in rows:
                alerts.append({
                    "id": row["id"],
                    "serial_number": row["serial_number"],
                    "alert_type": row["alert_type"],
                    "device_name": row["device_name"] or "Unknown",
                    "device_type": row["device_type"] or "Unknown",
                    "comlab_id": row["comlab_id"],
                    "lab_name": row["lab_name"] or f"Lab {row['comlab_id']}",
                    "timestamp": row["timestamp"]
                })
        return jsonify({"success": True, "alerts": alerts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "alerts": []}), 500


@api_bp.route("/delete_alert/<int:alert_id>", methods=["DELETE"])
@login_required
@limiter.limit("30 per minute")
def delete_alert(alert_id):
    """Delete an alert"""
    try:
        AlertService.delete_alert(alert_id)
        return jsonify({"success": True})
    except Exception as e:
        print("Error deleting alert:", e)
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/deleted_alerts/<comlab_id>")
def deleted_alerts(comlab_id):
    """Get deleted alerts for a lab"""
    conn = sqlite3.connect(Config.DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT a.id, a.serial_number, a.alert_type, a.device_name, a.device_type, a.user_id, a.timestamp, b.unique_id
        FROM peripheral_alerts a
        INNER JOIN peripherals b ON a.serial_number = b.serial_number
        WHERE a.deleted = 1 AND a.location = ?
        ORDER BY timestamp DESC
    """, (comlab_id,))
    rows = cur.fetchall()

    return jsonify([
        {
            "id": r[0],
            "serial_number": r[1],
            "alert_type": r[2],
            "device_name": r[3],
            "device_type": r[4],
            "user_id": r[5],
            "timestamp": r[6],
            "unique_id": r[7]
        }
        for r in rows
    ])


@api_bp.route("/restore_alert/<alert_id>", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def restore_alert(alert_id):
    """Restore a deleted alert"""
    success = AlertService.restore_alert(alert_id)
    return jsonify({"success": success})


@api_bp.route("/update_peripheral_remarks", methods=["POST"])
@user_required
@limiter.limit("30 per minute")
def update_peripheral_remarks():
    """Update peripheral remarks"""
    data = request.json
    unique_id = data["unique_id"]
    new_remarks = data["remarks"]
    user = session.get("username")

    old_remarks = Peripheral.get_remarks(unique_id)
    Peripheral.update_remarks(unique_id, new_remarks)

    # Insert history
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO peripheral_remarks_history
            (unique_id, old_remarks, new_remarks, updated_by)
            VALUES (?,?,?,?)
        """, (unique_id, old_remarks, new_remarks, user))
        conn.commit()

    return jsonify({"success": True})


@api_bp.route("/peripheral/<unique_id>/remarks_history")
def remarks_history(unique_id):
    """Get remarks history for a peripheral"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT old_remarks, new_remarks, updated_by, updated_at
            FROM peripheral_remarks_history
            WHERE unique_id=?
            ORDER BY updated_at DESC
        """, (unique_id,))
        rows = cur.fetchall()

    return jsonify([
        {
            "old": r[0],
            "new": r[1],
            "by": r[2],
            "at": r[3]
        } for r in rows
    ])


@api_bp.route('/api/check_logout')
def check_logout():
    """Check if user should be force logged out"""
    try:
        if "username" in session:
            username = session["username"]
            if User.check_force_logout(username):
                # Reset force_logout flag
                User.set_force_logout(username, 0)
                with sqlite3.connect(Config.DB_FILE) as conn:
                    cur = conn.cursor()
                    cur.execute("DELETE FROM active_sessions WHERE student_id=?", (username,))
                    conn.commit()
                return jsonify({'force_logout': True})
        return jsonify({'force_logout': False})
    except Exception as e:
        print(f"Error in /api/check_logout: {e}")
        return jsonify({'error': str(e)}), 500


@api_bp.route("/api/delete_device", methods=["POST"])
@login_required
@limiter.limit("10 per minute")
def delete_device():
    """Delete a device"""
    data = request.get_json()
    device_id = data.get("id")

    if not device_id:
        return jsonify({"success": False, "message": "Device ID not provided"}), 400

    try:
        Device.delete(device_id)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/api/detect_devices", methods=["GET"])
def detect_devices():
    """Detect currently connected USB devices using Windows SetupAPI"""
    try:
        import platform
        if platform.system() != "Windows":
            return jsonify({
                "success": False,
                "error": "Not Windows",
                "message": "Device detection is only available on Windows. This feature uses Windows SetupAPI (SetupDi* functions) which requires Windows."
            }), 400
        
        from app.utils.device_detector import get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
        
        if not IS_WINDOWS:
            return jsonify({
                "success": False,
                "error": "Not Windows",
                "message": "Device detection requires Windows."
            }), 400
        
        if not WIN32_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Windows API not available",
                "message": "pywin32 module is not available. Install it with: pip install pywin32"
            }), 500
        
        devices = get_connected_devices()
        
        return jsonify({
            "success": True,
            "devices": devices,
            "count": len(devices),
            "platform": "Windows",
            "source": "Windows SetupAPI (SetupDi* functions)"
        })
    except ImportError as e:
        return jsonify({
            "success": False,
            "error": "Import Error",
            "message": f"Required Windows modules not available: {str(e)}. Install with: pip install pywin32"
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to detect devices. Ensure you're running on Windows with proper permissions and pywin32 installed."
        }), 500


@api_bp.route("/api/detect_new_device", methods=["POST"])
@user_required
@limiter.limit("10 per minute")
def detect_new_device():
    """Detect newly plugged-in devices by comparing with previous Windows SetupAPI device list"""
    try:
        import platform
        if platform.system() != "Windows":
            return jsonify({
                "success": False,
                "error": "Not Windows",
                "message": "Device detection is only available on Windows."
            }), 400
        
        from app.utils.device_detector import detect_new_device, WIN32_AVAILABLE, IS_WINDOWS
        
        if not IS_WINDOWS or not WIN32_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Windows API not available",
                "message": "Windows SetupAPI access is not available. Ensure pywin32 is installed: pip install pywin32"
            }), 500
        
        data = request.get_json() or {}
        previous_keys = data.get("previous_device_keys", [])
        
        # Call detect_new_device with proper error handling
        try:
            new_devices, current_keys = detect_new_device(previous_keys)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in detect_new_device: {e}")
            print(error_trace)
            return jsonify({
                "success": False,
                "error": str(e),
                "message": f"Failed to detect new device: {str(e)}"
            }), 500
        
        # Ensure we have valid return values
        if not isinstance(new_devices, list):
            new_devices = []
        if not isinstance(current_keys, set):
            current_keys = set()
        
        return jsonify({
            "success": True,
            "new_devices": new_devices,
            "current_device_keys": list(current_keys),
            "has_new_device": len(new_devices) > 0,
            "platform": "Windows",
            "source": "Windows SetupAPI (SetupDi* functions)"
        })
    except ImportError as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": "Import Error",
            "message": f"Required Windows modules not available: {str(e)}"
        }), 500
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Unexpected error in detect_new_device API: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to detect new device: {str(e)}. Check Windows SetupAPI availability."
        }), 500


@api_bp.route("/api/check_windows_compatibility", methods=["GET"])
def check_windows_compatibility():
    """Check Windows device detection compatibility and status"""
    try:
        from app.utils.device_detector import check_windows_compatibility
        status = check_windows_compatibility()
        return jsonify({
            "success": True,
            **status
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to check Windows compatibility."
        }), 500


@api_bp.route("/api/get_student_profile", methods=["GET"])
def get_student_profile():
    """Get student profile information"""
    from app.models.user import User
    
    username = request.args.get("username")
    if not username:
        return jsonify({"success": False, "message": "Username not provided"}), 400
    
    try:
        profile = User.get_profile(username)
        if profile:
            return jsonify({
                "success": True,
                "profile": {
                    "username": profile[0],
                    "name": profile[1],
                    "email": profile[2],
                    "grade": profile[3],
                    "section": profile[4],
                    "contact": profile[5],
                    "profile_pic": profile[6] if len(profile) > 6 else None
                }
            })
        else:
            return jsonify({"success": False, "message": "Student not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@api_bp.route("/api/get_current_device_info", methods=["GET"])
def get_current_device_info():
    """Get current device information with unique ID"""
    try:
        import uuid
        import platform
        from app.utils.network_scanner import get_local_network_info, get_mac_address, detect_device_type
        
        # Get hostname
        hostname = get_hostname()
        
        # Get network info
        network_info = get_local_network_info()
        ip_address = network_info.get("local_ip") if network_info else None
        
        # Get MAC address
        mac_address = None
        if ip_address:
            mac_address = get_mac_address(ip_address)
            # If MAC not found, try to get from first network interface
            if not mac_address:
                try:
                    import subprocess
                    if platform.system().lower() == "windows":
                        result = subprocess.run(
                            ["getmac", "/fo", "csv", "/nh"],
                            capture_output=True,
                            timeout=2,
                            text=True
                        )
                        if result.returncode == 0 and result.stdout:
                            lines = result.stdout.strip().split('\n')
                            if lines:
                                mac_address = lines[0].split(',')[0].strip().replace('-', ':').upper()
                    else:
                        # Linux/Mac - try netifaces if available
                        try:
                            import netifaces
                            interfaces = netifaces.interfaces()
                            for iface in interfaces:
                                addrs = netifaces.ifaddresses(iface)
                                if netifaces.AF_LINK in addrs:
                                    mac_address = addrs[netifaces.AF_LINK][0]['addr'].upper()
                                    break
                        except ImportError:
                            # netifaces not available, skip
                            pass
                except Exception:
                    pass
        
        # Generate unique ID based on MAC address or hostname
        if mac_address:
            # Use MAC address to generate UUID (deterministic)
            unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{mac_address}-{hostname}"))
        else:
            # Fallback: use hostname-based UUID
            unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, hostname))
        
        # Detect device type
        device_type = detect_device_type(hostname, mac_address)
        
        return jsonify({
            "success": True,
            "hostname": hostname,
            "ip_address": ip_address,
            "mac_address": mac_address or "Unknown",
            "device_type": device_type,
            "unique_id": unique_id,
            "platform": platform.system(),
            "platform_release": platform.release()
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error getting device info: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get device information: {str(e)}"
        }), 500


@api_bp.route("/api/scan_network_devices", methods=["GET"])
def scan_network_devices():
    """Scan local network for devices (PCs, laptops, mobile devices)"""
    try:
        from app.utils.network_scanner import scan_network_devices_fast, get_local_network_info, scan_network_devices
        
        # Get network info first
        network_info = get_local_network_info()
        
        # Try fast ARP-based scanning first
        devices = scan_network_devices_fast()
        
        # If ARP scan didn't find many devices, try ping-based scan
        if len(devices) < 3:
            try:
                ping_devices = scan_network_devices(max_hosts=50, timeout=0.3)
                # Merge results, avoiding duplicates
                existing_ips = {d["ip"] for d in devices}
                for device in ping_devices:
                    if device["ip"] not in existing_ips:
                        devices.append(device)
            except Exception as e:
                print(f"Ping scan failed: {e}")
        
        return jsonify({
            "success": True,
            "devices": devices,
            "count": len(devices),
            "network_info": network_info
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error scanning network devices: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to scan network devices: {str(e)}"
        }), 500


@api_bp.route("/api/get_peripherals", methods=["GET"])
def get_peripherals():
    """Get peripherals for a specific PC, including unregistered devices"""
    try:
        pc_tag = request.args.get("pc_tag")
        lab_id = request.args.get("lab_id", type=int)
        include_unregistered = request.args.get("include_unregistered", "false").lower() == "true"
        
        if not pc_tag or not lab_id:
            return jsonify({
                "success": False,
                "error": "Missing parameters",
                "message": "pc_tag and lab_id are required."
            }), 400
        
        peripherals = Peripheral.get_by_pc(pc_tag, lab_id)
        # Convert Row objects to dictionaries, ensuring all fields including remarks are included
        peripherals_list = []
        for p in peripherals:
            p_dict = dict(p)
            # Ensure remarks field exists (handle None/empty cases)
            if 'remarks' not in p_dict or p_dict['remarks'] is None:
                p_dict['remarks'] = ''
            peripherals_list.append(p_dict)
        
        # Get registered unique IDs and vendor/product combinations
        registered_unique_ids = {p.get("unique_id", "") for p in peripherals_list if p.get("unique_id")}
        registered_vendor_product = set()
        for p in peripherals_list:
            vendor_id = p.get("vendor_id", "")
            product_id = p.get("product_id", "")
            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                registered_vendor_product.add(f"{vendor_id}_{product_id}")
        
        # Detect unregistered devices if requested
        unregistered_devices = []
        if include_unregistered:
            try:
                import platform
                if platform.system() == "Windows":
                    from app.utils.device_detector import get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
                    if IS_WINDOWS and WIN32_AVAILABLE:
                        current_devices = get_connected_devices()
                        seen_vendor_product = set()  # Track to avoid duplicates
                        for device in current_devices:
                            unique_id = device.get("unique_id", "")
                            vendor_id = device.get("vendor", "")
                            product_id = device.get("product", "")
                            
                            # Skip if already registered by unique_id
                            if unique_id and unique_id in registered_unique_ids:
                                continue
                            
                            # Skip if already registered by vendor/product (same device model)
                            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                                vendor_product_key = f"{vendor_id}_{product_id}"
                                if vendor_product_key in registered_vendor_product:
                                    continue  # This device model is already registered
                                
                                # Also skip if we've already added this vendor/product combo to unregistered list
                                if vendor_product_key in seen_vendor_product:
                                    continue  # Avoid duplicate entries for same device model
                                seen_vendor_product.add(vendor_product_key)
                            
                            # This is an unregistered device
                            unregistered_devices.append({
                                "name": device.get("type", "Unknown Device"),
                                "brand": device.get("name", "Unknown"),
                                "serial_number": device.get("unique_id", ""),
                                "unique_id": unique_id,
                                "status": "connected",
                                "remarks": "⚠️ UNREGISTERED DEVICE",
                                "is_unregistered": True,
                                "vendor": vendor_id,
                                "product": product_id
                            })
            except Exception as e:
                print(f"Could not detect unregistered devices: {e}")
        
        return jsonify({
            "success": True,
            "peripherals": peripherals_list,
            "unregistered_devices": unregistered_devices,
            "count": len(peripherals_list),
            "unregistered_count": len(unregistered_devices)
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error getting peripherals: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to get peripherals: {str(e)}"
        }), 500


@api_bp.route("/api/check_disconnected_devices", methods=["POST"])
@user_required
@limiter.limit("10 per minute")
def check_disconnected_devices():
    """Check for disconnected devices and update their status"""
    try:
        import platform
        if platform.system() != "Windows":
            return jsonify({
                "success": False,
                "error": "Not Windows",
                "message": "Device detection is only available on Windows."
            }), 400
        
        from app.utils.device_detector import detect_disconnected_devices, get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
        from app.models.peripheral import Peripheral
        
        if not IS_WINDOWS or not WIN32_AVAILABLE:
            return jsonify({
                "success": False,
                "error": "Windows API not available",
                "message": "Windows SetupAPI access is not available. Ensure pywin32 is installed."
            }), 500
        
        data = request.get_json() or {}
        pc_tag = data.get("pc_tag")
        lab_id = data.get("lab_id")
        
        if not pc_tag or not lab_id:
            return jsonify({
                "success": False,
                "error": "Missing parameters",
                "message": "pc_tag and lab_id are required."
            }), 400
        
        # Get registered peripherals for this PC
        peripherals = Peripheral.get_by_pc(pc_tag, lab_id)
        # Convert Row objects to dictionaries for easier access
        peripherals_dict = [dict(p) for p in peripherals]
        registered_unique_ids = [p.get("unique_id", "") for p in peripherals_dict if p.get("unique_id")]
        
        # Build map of vendor/product combinations for registered devices
        registered_vendor_product = {}
        for p in peripherals_dict:
            vendor_id = p.get("vendor_id", "")
            product_id = p.get("product_id", "")
            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                key = f"{vendor_id}_{product_id}"
                registered_vendor_product[key] = {
                    "vendor_id": vendor_id,
                    "product_id": product_id,
                    "peripheral": p
                }
        
        # Get current connected devices
        current_devices = get_connected_devices()
        current_unique_ids = {dev.get("unique_id", "") for dev in current_devices if dev.get("unique_id")}
        
        # Build map of current vendor/product combinations
        current_vendor_product = {}
        for dev in current_devices:
            vendor_id = dev.get("vendor", "")
            product_id = dev.get("product", "")
            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                key = f"{vendor_id}_{product_id}"
                current_vendor_product[key] = {
                    "vendor_id": vendor_id,
                    "product_id": product_id,
                    "device": dev
                }
        
        # Detect disconnected devices by vendor/product (more reliable than unique_id)
        # A device is disconnected if its vendor/product combo is registered but not currently connected
        disconnected_vendor_product = []
        for key, reg_info in registered_vendor_product.items():
            if key not in current_vendor_product:
                # This device model is not currently connected
                disconnected_vendor_product.append(reg_info)
        
        # Detect reconnected devices by vendor/product
        # A device is reconnected if its vendor/product combo is registered, currently connected, but status is "unplugged"
        reconnected_vendor_product = []
        for key, reg_info in registered_vendor_product.items():
            if key in current_vendor_product:
                peripheral = reg_info["peripheral"]
                if peripheral.get("status", "").lower() == "unplugged":
                    reconnected_vendor_product.append(reg_info)
        
        # Update status for disconnected devices (by vendor/product)
        disconnected_count = 0
        for reg_info in disconnected_vendor_product:
            peripheral = reg_info["peripheral"]
            if peripheral.get("status", "").lower() == "connected":
                Peripheral.update_status_by_vendor_product(
                    reg_info["vendor_id"],
                    reg_info["product_id"],
                    pc_tag,
                    "unplugged"
                )
                disconnected_count += 1
        
        # Update status for reconnected devices (by vendor/product)
        reconnected_count = 0
        for reg_info in reconnected_vendor_product:
            peripheral = reg_info["peripheral"]
            if peripheral.get("status", "").lower() == "unplugged":
                Peripheral.update_status_by_vendor_product(
                    reg_info["vendor_id"],
                    reg_info["product_id"],
                    pc_tag,
                    "connected"
                )
                reconnected_count += 1
        
        # Detect newly connected devices (both registered and unregistered)
        # This helps the frontend know when to refresh the full list
        newly_connected_registered = []
        newly_connected_unregistered = []
        
        # Check for registered devices that just connected (by vendor/product)
        # A device is newly connected if its vendor/product combo is registered, currently connected, 
        # but status was not "connected" before
        for key, reg_info in registered_vendor_product.items():
            if key in current_vendor_product:
                peripheral = reg_info["peripheral"]
                status = peripheral.get("status", "").lower()
                if status not in ["connected"]:
                    # This device model just connected
                    newly_connected_registered.append({
                        "vendor_id": reg_info["vendor_id"],
                        "product_id": reg_info["product_id"],
                        "unique_id": peripheral.get("unique_id", "")
                    })
        
        # Check for unregistered devices (connected but not in database by vendor/product)
        for device in current_devices:
            vendor_id = device.get("vendor", "")
            product_id = device.get("product", "")
            unique_id = device.get("unique_id", "")
            
            # Skip if registered by unique_id
            if unique_id and unique_id in registered_unique_ids:
                continue
            
            # Skip if registered by vendor/product
            if vendor_id and product_id and vendor_id != "UNKNOWN" and product_id != "UNKNOWN":
                vendor_product_key = f"{vendor_id}_{product_id}"
                if vendor_product_key in registered_vendor_product:
                    continue  # This device model is already registered
            
            # This is an unregistered device
            newly_connected_unregistered.append({
                "unique_id": unique_id,
                "name": device.get("type", "Unknown Device"),
                "brand": device.get("name", "Unknown"),
                "vendor": vendor_id,
                "product": product_id
            })
        
        # If there are any changes, indicate that a full refresh is needed
        needs_refresh = (disconnected_count > 0 or reconnected_count > 0 or 
                        len(newly_connected_registered) > 0 or len(newly_connected_unregistered) > 0)
        
        # Build lists of unique_ids for disconnected/reconnected devices for backward compatibility
        disconnected_unique_ids = []
        reconnected_unique_ids = []
        for reg_info in disconnected_vendor_product:
            peripheral = reg_info["peripheral"]
            unique_id = peripheral.get("unique_id", "")
            if unique_id:
                disconnected_unique_ids.append(unique_id)
        for reg_info in reconnected_vendor_product:
            peripheral = reg_info["peripheral"]
            unique_id = peripheral.get("unique_id", "")
            if unique_id:
                reconnected_unique_ids.append(unique_id)
        
        return jsonify({
            "success": True,
            "disconnected_ids": disconnected_unique_ids,
            "reconnected_ids": reconnected_unique_ids,
            "newly_connected_registered": newly_connected_registered,
            "newly_connected_unregistered": newly_connected_unregistered,
            "disconnected_count": disconnected_count,
            "reconnected_count": reconnected_count,
            "needs_refresh": needs_refresh,
            "message": f"Updated {disconnected_count} device(s) to unplugged, {reconnected_count} device(s) to connected."
        })
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error checking disconnected devices: {e}")
        print(error_trace)
        return jsonify({
            "success": False,
            "error": str(e),
            "message": f"Failed to check disconnected devices: {str(e)}"
        }), 500