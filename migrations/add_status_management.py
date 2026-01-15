"""Database migration: Add status management tables and columns"""
import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from app.config import Config
    db_file = Config.DB_FILE
except ImportError:
    # Fallback if app module not available
    db_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")

def migrate():
    """Add status management tables and columns"""
    
    with sqlite3.connect(db_file) as conn:
        cur = conn.cursor()
        
        # Create peripheral_status_history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS peripheral_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                peripheral_id INTEGER NOT NULL,
                old_status TEXT,
                new_status TEXT NOT NULL,
                reason TEXT,
                updated_by TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (peripheral_id) REFERENCES peripherals(id)
            )
        """)
        
        # Add status tracking columns to peripherals table
        cur.execute("PRAGMA table_info(peripherals)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "status_updated_by" not in columns:
            cur.execute("ALTER TABLE peripherals ADD COLUMN status_updated_by TEXT")
        
        if "status_updated_at" not in columns:
            cur.execute("ALTER TABLE peripherals ADD COLUMN status_updated_at TEXT")
        
        if "status_reason" not in columns:
            cur.execute("ALTER TABLE peripherals ADD COLUMN status_reason TEXT")
        
        # Add password reset flag to users table
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if "password_reset_required" not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN password_reset_required INTEGER DEFAULT 0")
        
        if "password_reset_by" not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN password_reset_by TEXT")
        
        if "password_reset_at" not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN password_reset_at TEXT")
        
        # Create system_settings table for admin settings
        cur.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                description TEXT,
                updated_by TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create audit_log table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                details TEXT,
                ip_address TEXT,
                timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for performance
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_peripheral_status ON peripherals(status, lab_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_peripheral_unique_id ON peripherals(unique_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_device_comlab_tag ON devices(comlab_id, tag)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_location_deleted ON peripheral_alerts(location, deleted, alert_type)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_status_history_peripheral ON peripheral_status_history(peripheral_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action)")
        except sqlite3.OperationalError:
            pass  # Indexes might already exist
        
        conn.commit()
        print("Migration completed: Status management tables and columns added")

if __name__ == "__main__":
    migrate()

