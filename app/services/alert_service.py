"""Alert service for handling USB events and peripheral alerts"""
import sqlite3
from datetime import datetime
from app.config import Config
from app.models.peripheral import Peripheral


class AlertService:
    """Service for handling alerts and USB events"""
    
    @staticmethod
    def process_usb_event(event_data):
        """Process USB event and update peripheral status/alert"""
        try:
            conn = sqlite3.connect(Config.DB_FILE)
            cur = conn.cursor()
            
            # Verify that the user is logged in on the PC where the event originated
            user_id = event_data.get('user_id')
            pc_tag = event_data.get('pc_tag')
            
            if user_id and pc_tag:
                # Check if user is logged in on this PC
                cur.execute("SELECT pc_tag FROM active_sessions WHERE student_id = ?", (user_id,))
                session_row = cur.fetchone()
                
                if session_row:
                    session_pc_tag = session_row[0]
                    # If the PC tag doesn't match, reject the event
                    if session_pc_tag != pc_tag:
                        conn.close()
                        return {
                            "status": "rejected",
                            "message": f"User is logged in on different PC ({session_pc_tag}). Event from {pc_tag} rejected.",
                            "rejected": True
                        }
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Insert USB event
            cur.execute("""
                INSERT INTO usb_devices 
                (event_type, device_type, vendor, product, unique_id, username, timestamp, pc_tag, user_id, device_name, location)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_data['event_type'], event_data['device_type'], event_data['vendor'],
                event_data['product'], event_data['unique_id'], event_data['username'],
                timestamp, event_data['pc_tag'], event_data['user_id'],
                event_data['device_name'], event_data['location']
            ))
            
            new_status = None
            alert_type = None
            
            if event_data['event_type'] == "connected":
                device = Peripheral.get_by_serial(
                    event_data['device_type'],
                    event_data['location'],
                    event_data['device_name']
                )
                
                if device:
                    serial_number = device[0]
                    if serial_number != event_data['unique_id']:
                        new_status = "replaced"
                        alert_type = "replaced"
                    else:
                        new_status = "connected"
                    
                    Peripheral.update_status(
                        event_data['device_type'],
                        event_data['location'],
                        event_data['device_name'],
                        new_status
                    )
                    
                    if alert_type:
                        AlertService.create_alert(
                            event_data['unique_id'],
                            alert_type,
                            timestamp,
                            event_data['device_name'],
                            event_data['location'],
                            event_data['event_type'],
                            event_data['device_type'],
                            event_data['user_id']
                        )
                        
            elif event_data['event_type'] == "disconnected":
                new_status = "unplugged"
            
            if new_status:
                Peripheral.update_status_by_serial(
                    event_data['device_type'],
                    event_data['unique_id'],
                    event_data['device_name'],
                    new_status
                )
            
            # Insert peripheral log
            cur.execute("""
                INSERT INTO peripheral_logs (unique_id, event_type, device_type, timestamp, device_name)
                VALUES (?, ?, ?, ?, ?)
            """, (event_data['unique_id'], event_data['event_type'], event_data['device_type'], timestamp, event_data['device_name']))
            
            # Check for faulty device (3+ connect/disconnect cycles in 10 minutes)
            alert_type = AlertService.check_faulty_device(cur, event_data['unique_id'], timestamp, event_data)
            
            # Check for missing device (disconnected > 10 minutes)
            AlertService.check_missing_device(cur, event_data['unique_id'], timestamp, event_data)
            
            conn.commit()
            conn.close()
            
            return {"status": "success", "alert": alert_type}
            
        except sqlite3.Error as e:
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def check_faulty_device(cur, unique_id, timestamp, event_data):
        """Check if device is faulty (3+ cycles in 10 minutes)"""
        cur.execute("""
            SELECT event_type
            FROM peripheral_logs
            WHERE unique_id = ?
              AND datetime(timestamp) >= datetime('now', '-10 minutes')
            ORDER BY datetime(timestamp) ASC
        """, (unique_id,))
        
        events = [row[0] for row in cur.fetchall()]
        cycle_count = 0
        
        for i in range(len(events) - 1):
            if events[i] == "connected" and events[i + 1] == "disconnected":
                cycle_count += 1
        
        if cycle_count >= 3:
            cur.execute("""
                UPDATE peripherals SET status = 'faulty'
                WHERE serial_number = ?
            """, (unique_id,))
            
            AlertService.create_alert(
                unique_id,
                "faulty",
                timestamp,
                event_data['device_name'],
                event_data['location'],
                event_data['event_type'],
                event_data['device_type'],
                event_data['user_id']
            )
            return "faulty"
        return None
    
    @staticmethod
    def check_missing_device(cur, unique_id, timestamp, event_data):
        """Check if device is missing (disconnected > 10 minutes)"""
        cur.execute("""
            SELECT timestamp FROM peripheral_logs
            WHERE unique_id = ? AND event_type = 'disconnected'
            ORDER BY timestamp DESC LIMIT 1
        """, (unique_id,))
        
        last_unplug = cur.fetchone()
        
        if last_unplug:
            ts = last_unplug[0]
            try:
                last_unplug_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            except:
                last_unplug_time = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
            
            now = datetime.now()
            
            if (now - last_unplug_time).total_seconds() >= 600:  # 10 minutes
                cur.execute("""
                    UPDATE peripherals SET status = 'missing'
                    WHERE serial_number = ?
                """, (unique_id,))
                
                AlertService.create_alert(
                    unique_id,
                    "missing",
                    timestamp,
                    event_data['device_name'],
                    event_data['location'],
                    event_data['event_type'],
                    event_data['device_type'],
                    event_data['user_id']
                )
    
    @staticmethod
    def create_alert(serial_number, alert_type, timestamp, device_name, location, event_type, device_type, user_id):
        """Create a peripheral alert"""
        conn = sqlite3.connect(Config.DB_FILE)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO peripheral_alerts (serial_number, alert_type, timestamp, device_name, location, event_type, device_type, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (serial_number, alert_type, timestamp, device_name, location, event_type, device_type, user_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_alerts_by_location(location):
        """Get alerts for a specific location"""
        conn = sqlite3.connect(Config.DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT B.unique_id, A.* FROM peripheral_alerts A 
            INNER JOIN peripherals B ON A.serial_number = B.serial_number 
            WHERE A.location = ? AND A.deleted = 0 
            ORDER BY timestamp DESC
        """, (location,))
        alerts = cur.fetchall()
        conn.close()
        return alerts
    
    @staticmethod
    def delete_alert(alert_id):
        """Soft delete an alert"""
        conn = sqlite3.connect(Config.DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE peripheral_alerts SET deleted = 1 WHERE id=?", (alert_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def restore_alert(alert_id):
        """Restore a deleted alert"""
        conn = sqlite3.connect(Config.DB_FILE)
        cur = conn.cursor()
        cur.execute("UPDATE peripheral_alerts SET deleted=0 WHERE id=?", (alert_id,))
        conn.commit()
        success = cur.rowcount > 0
        conn.close()
        return success

