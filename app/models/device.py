"""Device model and database operations"""
import sqlite3
from app.config import Config


class Device:
    """Device model"""
    
    @staticmethod
    def create(tag, location, hostname, ip_address, comlab_id, unique_id=None, mac_address=None):
        """Create a new device"""
        from app.utils.helpers import get_current_timestamp
        created_at = get_current_timestamp()
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            # Check if columns exist, add them if they don't
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(devices)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Add mac_address column if it doesn't exist
            if "mac_address" not in columns:
                try:
                    conn.execute("ALTER TABLE devices ADD COLUMN mac_address TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            # Add unique_id column if it doesn't exist
            if "unique_id" not in columns:
                try:
                    conn.execute("ALTER TABLE devices ADD COLUMN unique_id TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            # Use correct column name (handle typo in schema)
            ip_column = "ip_addres" if "ip_addres" in columns else "ip_address"
            created_column = "created_a" if "created_a" in columns else "created_at"
            
            # Refresh columns after potential ALTER TABLE
            cur.execute("PRAGMA table_info(devices)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Build insert query dynamically
            has_mac = "mac_address" in columns
            has_unique = "unique_id" in columns
            
            if has_mac and has_unique:
                conn.execute(f"""
                    INSERT INTO devices (tag, location, hostname, {ip_column}, {created_column}, comlab_id, mac_address, unique_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tag, location, hostname, ip_address, created_at, comlab_id, mac_address, unique_id))
            elif has_unique:
                conn.execute(f"""
                    INSERT INTO devices (tag, location, hostname, {ip_column}, {created_column}, comlab_id, unique_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tag, location, hostname, ip_address, created_at, comlab_id, unique_id))
            elif has_mac:
                conn.execute(f"""
                    INSERT INTO devices (tag, location, hostname, {ip_column}, {created_column}, comlab_id, mac_address)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (tag, location, hostname, ip_address, created_at, comlab_id, mac_address))
            else:
                conn.execute(f"""
                    INSERT INTO devices (tag, location, hostname, {ip_column}, {created_column}, comlab_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tag, location, hostname, ip_address, created_at, comlab_id))
            conn.commit()
    
    @staticmethod
    def get_by_tag(tag):
        """Get device by tag"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, tag, location, hostname FROM devices WHERE tag = ?", (tag,))
            return cur.fetchone()
    
    @staticmethod
    def get_by_hostname(hostname):
        """Get device by hostname"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT tag, location FROM devices WHERE hostname = ?", (hostname,))
            return cur.fetchone()
    
    @staticmethod
    def get_by_location(location):
        """Get all devices in a location (by comlab_id)"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Check if mac_address, unique_id, and ip_address columns exist
            cur.execute("PRAGMA table_info(devices)")
            columns = [row[1] for row in cur.fetchall()]
            
            has_mac = "mac_address" in columns
            has_unique = "unique_id" in columns
            # Check for both ip_address and ip_addres (typo in schema)
            has_ip = "ip_address" in columns or "ip_addres" in columns
            ip_column = "ip_addres" if "ip_addres" in columns else "ip_address"
            
            # Build SELECT query dynamically
            select_fields = ["id", "tag", "hostname"]
            if has_ip:
                select_fields.append(ip_column)
            if has_mac:
                select_fields.append("mac_address")
            if has_unique:
                select_fields.append("unique_id")
            
            query = f"SELECT {', '.join(select_fields)} FROM devices WHERE comlab_id = ?"
            cur.execute(query, (location,))
            return cur.fetchall()
    
    @staticmethod
    def delete(device_id):
        """Delete a device"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM devices WHERE id=?", (device_id,))
            conn.commit()
    
    @staticmethod
    def get_all():
        """Get all devices"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, tag, location, hostname FROM devices")
            return cur.fetchall()

