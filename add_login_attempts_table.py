"""Add login_attempts table and update users table if missing"""
import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")

def add_missing_tables():
    """Add login_attempts table and update users table columns if they don't exist"""
    with sqlite3.connect(DB_FILE) as conn:
        cur = conn.cursor()
        
        # Check if login_attempts table exists
        cur.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='login_attempts'
        """)
        if not cur.fetchone():
            print("Creating login_attempts table...")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_attempts
                (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    ip_address TEXT,
                    success INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)
            print("[OK] login_attempts table created")
        else:
            print("[OK] login_attempts table already exists")
        
        # Check and add missing columns to users table
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'last_login' not in columns:
            print("Adding last_login column to users table...")
            cur.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
            print("[OK] last_login column added")
        
        if 'failed_login_count' not in columns:
            print("Adding failed_login_count column to users table...")
            cur.execute("ALTER TABLE users ADD COLUMN failed_login_count INTEGER DEFAULT 0")
            print("[OK] failed_login_count column added")
        
        if 'account_locked_until' not in columns:
            print("Adding account_locked_until column to users table...")
            cur.execute("ALTER TABLE users ADD COLUMN account_locked_until TEXT")
            print("[OK] account_locked_until column added")
        
        conn.commit()
        print("\n[OK] Database update complete!")

if __name__ == "__main__":
    print("Updating database schema...")
    print("=" * 50)
    try:
        add_missing_tables()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()

