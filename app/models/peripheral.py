"""Peripheral model and database operations"""
import sqlite3
from app.config import Config


class Peripheral:
    """Peripheral model"""
    
    @staticmethod
    def create(name, brand, assigned_pc, lab_id, unique_id="", serial_number="", status="CONNECTED", remarks="", vendor_id=None, product_id=None):
        """Create a new peripheral"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            # Check if vendor_id and product_id columns exist, add them if they don't
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            
            if "vendor_id" not in columns:
                try:
                    conn.execute("ALTER TABLE peripherals ADD COLUMN vendor_id TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            if "product_id" not in columns:
                try:
                    conn.execute("ALTER TABLE peripherals ADD COLUMN product_id TEXT")
                    conn.commit()
                except sqlite3.OperationalError:
                    pass  # Column might already exist
            
            # Refresh columns after potential ALTER TABLE
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            
            # Build insert query dynamically based on available columns
            if "vendor_id" in columns and "product_id" in columns:
                cur.execute("""
                    INSERT INTO peripherals (name, brand, assigned_pc, lab_id, unique_id, serial_number, status, remarks, vendor_id, product_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, brand, assigned_pc, lab_id, unique_id, serial_number, status, remarks, vendor_id, product_id))
            else:
                cur.execute("""
                    INSERT INTO peripherals (name, brand, assigned_pc, lab_id, unique_id, serial_number, status, remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, brand, assigned_pc, lab_id, unique_id, serial_number, status, remarks))
            conn.commit()
            return cur.lastrowid
    
    @staticmethod
    def get_by_lab(lab_id):
        """Get all peripherals in a lab, only for PCs that exist in the devices table"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Check if vendor_id and product_id columns exist
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            has_vendor_product = "vendor_id" in columns and "product_id" in columns
            
            if has_vendor_product:
                cur.execute("""
                    SELECT p.id, p.name, p.brand, p.unique_id, p.serial_number, p.assigned_pc, p.status, p.remarks, p.vendor_id, p.product_id
                    FROM peripherals p
                    INNER JOIN devices d ON p.assigned_pc = d.tag AND d.comlab_id = p.lab_id
                    WHERE p.lab_id = ?
                """, (lab_id,))
            else:
                cur.execute("""
                    SELECT p.id, p.name, p.brand, p.unique_id, p.serial_number, p.assigned_pc, p.status, p.remarks 
                    FROM peripherals p
                    INNER JOIN devices d ON p.assigned_pc = d.tag AND d.comlab_id = p.lab_id
                    WHERE p.lab_id = ?
                """, (lab_id,))
            return cur.fetchall()
    
    @staticmethod
    def get_by_pc(assigned_pc, lab_id):
        """Get peripherals assigned to a PC, only if the PC exists in the devices table"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Check if vendor_id and product_id columns exist
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            has_vendor_product = "vendor_id" in columns and "product_id" in columns
            
            if has_vendor_product:
                cur.execute("""
                    SELECT p.id, p.name, p.brand, p.unique_id, p.serial_number, p.status, p.remarks, p.vendor_id, p.product_id
                    FROM peripherals p
                    INNER JOIN devices d ON p.assigned_pc = d.tag AND d.comlab_id = p.lab_id
                    WHERE p.assigned_pc = ? AND p.lab_id = ?
                """, (assigned_pc, lab_id))
            else:
                cur.execute("""
                    SELECT p.id, p.name, p.brand, p.unique_id, p.serial_number, p.status, p.remarks 
                    FROM peripherals p
                    INNER JOIN devices d ON p.assigned_pc = d.tag AND d.comlab_id = p.lab_id
                    WHERE p.assigned_pc = ? AND p.lab_id = ?
                """, (assigned_pc, lab_id))
            return cur.fetchall()
    
    @staticmethod
    def update_status(name, lab_id, assigned_pc, status):
        """Update peripheral status"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE peripherals SET status = ?
                WHERE name = ? AND lab_id = ? AND assigned_pc = ?
            """, (status, name, lab_id, assigned_pc))
            conn.commit()
    
    @staticmethod
    def update_status_by_serial(device_type, unique_id, device_name, status):
        """Update peripheral status by unique_id"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            # Update by unique_id (more reliable than serial_number)
            cur.execute("""
                UPDATE peripherals SET status = ?
                WHERE unique_id = ? AND assigned_pc = ?
            """, (status, unique_id, device_name))
            conn.commit()
    
    @staticmethod
    def update_status_by_unique_id(unique_id, pc_tag, status):
        """Update peripheral status by unique_id (simpler method)"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE peripherals SET status = ?
                WHERE unique_id = ? AND assigned_pc = ?
            """, (status, unique_id, pc_tag))
            conn.commit()
    
    @staticmethod
    def update_status_by_vendor_product(vendor_id, product_id, pc_tag, status):
        """Update peripheral status by vendor_id and product_id (for USB port changes)"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            # Check if vendor_id and product_id columns exist
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            has_vendor_product = "vendor_id" in columns and "product_id" in columns
            
            if has_vendor_product:
                cur.execute("""
                    UPDATE peripherals SET status = ?
                    WHERE vendor_id = ? AND product_id = ? AND assigned_pc = ?
                """, (status, vendor_id, product_id, pc_tag))
            else:
                # Fallback to unique_id if vendor/product columns don't exist
                # This shouldn't happen in normal operation, but handle gracefully
                pass
            conn.commit()
    
    @staticmethod
    def update(peripheral_id, name, brand, unique_id, serial_number, remarks):
        """Update peripheral details"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE peripherals
                SET name=?, brand=?, unique_id=?, serial_number=?, remarks=?
                WHERE id=?
            """, (name, brand, unique_id, serial_number, remarks, peripheral_id))
            conn.commit()
    
    @staticmethod
    def delete(peripheral_id):
        """Delete a peripheral"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM peripherals WHERE id = ?", (peripheral_id,))
            conn.commit()
    
    @staticmethod
    def get_by_serial(serial_number, lab_id, assigned_pc):
        """Get peripheral by serial number"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT serial_number FROM peripherals
                WHERE name = ? AND lab_id = ? AND assigned_pc = ?
            """, (serial_number, lab_id, assigned_pc))
            return cur.fetchone()
    
    @staticmethod
    def update_remarks(unique_id, remarks):
        """Update peripheral remarks"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE peripherals SET remarks=? WHERE unique_id=?", (remarks, unique_id))
            conn.commit()
    
    @staticmethod
    def get_remarks(unique_id):
        """Get peripheral remarks"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT remarks FROM peripherals WHERE unique_id=?", (unique_id,))
            result = cur.fetchone()
            return result[0] if result else ""
    
    @staticmethod
    def update_remarks_by_id(peripheral_id, remarks):
        """Update peripheral remarks by ID"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE peripherals SET remarks=? WHERE id=?", (remarks, peripheral_id))
            conn.commit()
    
    @staticmethod
    def get_by_vendor_product(vendor_id, product_id):
        """Get peripherals by vendor_id and product_id to check for duplicates"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            # Check if vendor_id and product_id columns exist
            cur.execute("PRAGMA table_info(peripherals)")
            columns = [row[1] for row in cur.fetchall()]
            
            if "vendor_id" in columns and "product_id" in columns:
                cur.execute("""
                    SELECT id, name, brand, unique_id, vendor_id, product_id
                    FROM peripherals
                    WHERE vendor_id = ? AND product_id = ?
                """, (vendor_id, product_id))
                return cur.fetchall()
            return []
    
    @staticmethod
    def get_by_id(peripheral_id):
        """Get peripheral by ID"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM peripherals WHERE id = ?", (peripheral_id,))
            return cur.fetchone()
    
    @staticmethod
    def update_status_manual(peripheral_id, new_status, reason=None, updated_by=None):
        """Manually update peripheral status with history tracking"""
        from app.models.status_history import StatusHistory
        from app.utils.helpers import get_current_timestamp
        from app.utils.constants import PERIPHERAL_STATUSES
        
        # Normalize status to lowercase
        new_status = new_status.lower()
        
        # Validate status
        if new_status not in PERIPHERAL_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            
            # Get current status
            cur.execute("SELECT status, status_updated_by, status_updated_at, status_reason FROM peripherals WHERE id = ?", (peripheral_id,))
            current = cur.fetchone()
            old_status = current[0] if current else None
            
            # Update status
            updated_at = get_current_timestamp()
            cur.execute("""
                UPDATE peripherals 
                SET status = ?, status_updated_by = ?, status_updated_at = ?, status_reason = ?
                WHERE id = ?
            """, (new_status, updated_by, updated_at, reason, peripheral_id))
            
            # Create history entry
            if old_status != new_status:
                StatusHistory.create(peripheral_id, old_status, new_status, reason, updated_by)
            
            conn.commit()
            return True
    
    @staticmethod
    def validate_status_transition(old_status, new_status):
        """Validate if status transition is allowed"""
        from app.utils.constants import STATUS_TRANSITIONS
        
        old_status = old_status.lower() if old_status else None
        new_status = new_status.lower()
        
        if old_status is None:
            return True  # Initial status assignment
        
        if old_status not in STATUS_TRANSITIONS:
            return False
        
        return new_status in STATUS_TRANSITIONS[old_status]

