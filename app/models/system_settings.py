"""System settings model"""
import sqlite3
from app.config import Config
from app.utils.helpers import get_current_timestamp


class SystemSettings:
    """System settings model"""
    
    @staticmethod
    def get(setting_key, default=None):
        """Get a system setting"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT setting_value FROM system_settings WHERE setting_key = ?", (setting_key,))
            result = cur.fetchone()
            return result[0] if result else default
    
    @staticmethod
    def set(setting_key, setting_value, description=None, updated_by=None):
        """Set a system setting"""
        updated_at = get_current_timestamp()
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT OR REPLACE INTO system_settings 
                (setting_key, setting_value, description, updated_by, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (setting_key, setting_value, description, updated_by, updated_at))
            conn.commit()
    
    @staticmethod
    def get_all():
        """Get all system settings"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM system_settings ORDER BY setting_key")
            return cur.fetchall()
    
    @staticmethod
    def delete(setting_key):
        """Delete a system setting"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM system_settings WHERE setting_key = ?", (setting_key,))
            conn.commit()

