"""Security utilities for authentication and rate limiting"""
import sqlite3
from datetime import datetime, timedelta
from app.config import Config


def record_login_attempt(username, ip_address, success=False):
    """Record a login attempt"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO login_attempts (username, ip_address, success, timestamp)
            VALUES (?, ?, ?, ?)
        """, (username, ip_address, 1 if success else 0, timestamp))
        conn.commit()


def get_failed_login_count(username, minutes=15):
    """Get count of failed login attempts in the last N minutes"""
    cutoff_time = (datetime.now() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) FROM login_attempts
            WHERE username = ? AND success = 0 AND timestamp > ?
        """, (username, cutoff_time))
        result = cur.fetchone()
        return result[0] if result else 0


def is_account_locked(username):
    """Check if account is locked due to too many failed attempts"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        # Check if account_locked_until column exists
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'account_locked_until' in columns:
            cur.execute("SELECT account_locked_until FROM users WHERE username = ?", (username,))
            result = cur.fetchone()
            if result and result[0]:
                try:
                    lock_until = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
                    if lock_until > datetime.now():
                        return True, lock_until
                except:
                    pass
        return False, None


def lock_account(username, minutes=30):
    """Lock account for specified minutes"""
    lock_until = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        # Check if account_locked_until column exists, if not add it
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'account_locked_until' not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN account_locked_until TEXT")
        
        cur.execute("UPDATE users SET account_locked_until = ?, failed_login_count = 0 WHERE username = ?", 
                   (lock_until, username))
        conn.commit()


def unlock_account(username):
    """Unlock account"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET account_locked_until = NULL, failed_login_count = 0 WHERE username = ?", 
                   (username,))
        conn.commit()


def increment_failed_login_count(username):
    """Increment failed login count"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        # Check if failed_login_count column exists
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'failed_login_count' not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN failed_login_count INTEGER DEFAULT 0")
        
        cur.execute("UPDATE users SET failed_login_count = COALESCE(failed_login_count, 0) + 1 WHERE username = ?", 
                   (username,))
        conn.commit()
        
        # Get current count
        cur.execute("SELECT failed_login_count FROM users WHERE username = ?", (username,))
        result = cur.fetchone()
        return result[0] if result and result[0] else 0


def reset_failed_login_count(username):
    """Reset failed login count after successful login"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET failed_login_count = 0 WHERE username = ?", (username,))
        conn.commit()


def update_last_login(username):
    """Update last login timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        # Check if last_login column exists
        cur.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'last_login' not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
        
        cur.execute("UPDATE users SET last_login = ? WHERE username = ?", (timestamp, username))
        conn.commit()


