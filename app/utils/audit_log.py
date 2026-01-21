"""Audit logging utility"""
import sqlite3
from app.config import Config
from app.utils.helpers import get_current_timestamp


def log_audit(user_id, action, resource_type=None, resource_id=None, details=None, ip_address=None):
    """Log an audit event"""
    timestamp = get_current_timestamp()
    
    try:
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO audit_log 
                (user_id, action, resource_type, resource_id, details, ip_address, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, action, resource_type, resource_id, details, ip_address, timestamp))
            conn.commit()
    except Exception as e:
        # Don't fail if audit logging fails
        print(f"Error logging audit event: {e}")


def get_audit_logs(user_id=None, action=None, limit=100):
    """Get audit logs"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        query = "SELECT * FROM audit_log WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cur.execute(query, params)
        return cur.fetchall()


