"""Status history model for tracking peripheral status changes"""
import sqlite3
from app.config import Config
from app.utils.helpers import get_current_timestamp


class StatusHistory:
    """Status history model"""
    
    @staticmethod
    def create(peripheral_id, old_status, new_status, reason=None, updated_by=None):
        """Create a status history entry"""
        updated_at = get_current_timestamp()
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO peripheral_status_history 
                (peripheral_id, old_status, new_status, reason, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (peripheral_id, old_status, new_status, reason, updated_by, updated_at))
            conn.commit()
            return cur.lastrowid
    
    @staticmethod
    def get_by_peripheral(peripheral_id, limit=50):
        """Get status history for a peripheral"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM peripheral_status_history
                WHERE peripheral_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (peripheral_id, limit))
            return cur.fetchall()
    
    @staticmethod
    def get_all(limit=100):
        """Get all status history entries"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT sh.*, p.name as peripheral_name, p.assigned_pc, p.lab_id
                FROM peripheral_status_history sh
                LEFT JOIN peripherals p ON sh.peripheral_id = p.id
                ORDER BY sh.updated_at DESC
                LIMIT ?
            """, (limit,))
            return cur.fetchall()


