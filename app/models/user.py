"""User model and database operations"""
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from app.config import Config


class User:
    """User model"""
    
    @staticmethod
    def create(username, name, password, role, grade=None, section=None, status="pending"):
        """Create a new user"""
        hashed_password = generate_password_hash(password)
        from app.utils.helpers import get_current_timestamp
        created_at = get_current_timestamp()
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (username, name, password, role, status, grade, section, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (username, name, hashed_password, role, status, grade, section, created_at))
            conn.commit()
    
    @staticmethod
    def get_by_username(username):
        """Get user by username"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, password, role, status, name FROM users WHERE username=?", (username,))
            return cur.fetchone()
    
    @staticmethod
    def verify_password(password_hash, password):
        """Verify password"""
        return check_password_hash(password_hash, password)
    
    @staticmethod
    def update_password(username, new_password):
        """Update user password"""
        hashed_password = generate_password_hash(new_password)
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET password=? WHERE username=?", (hashed_password, username))
            conn.commit()
    
    @staticmethod
    def get_pending_users():
        """Get all pending users"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, username, role, status, created_by FROM users WHERE status = ?", ("pending",))
            return cur.fetchall()
    
    @staticmethod
    def approve(user_id):
        """Approve a pending user"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET status='active' WHERE id=?", (user_id,))
            conn.commit()
    
    @staticmethod
    def reject(user_id):
        """Reject/delete a pending user"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
    
    @staticmethod
    def get_active_users(account_type="user"):
        """Get active users by type"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if account_type == "user":
                cur.execute("""
                    SELECT id, username, name, password, grade, section, role, created_at
                    FROM users
                    WHERE (role = 'user' OR role = 'professor') AND status = 'active'
                    ORDER BY id DESC
                """)
            else:  # admin
                cur.execute("""
                    SELECT id, username, name, password, created_at, role
                    FROM users
                    WHERE role = 'admin' AND status = 'active'
                    ORDER BY id DESC
                """)
            return cur.fetchall()
    
    @staticmethod
    def delete(user_id):
        """Delete a user"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
    
    @staticmethod
    def get_profile(username):
        """Get user profile"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT username, name, email, grade, section, contact, profile_pic FROM users WHERE username=?",
                (username,)
            )
            return cur.fetchone()
    
    @staticmethod
    def update_profile_picture(username, filepath):
        """Update user profile picture"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET profile_pic=? WHERE username=?", (filepath, username))
            conn.commit()
    
    @staticmethod
    def update_profile(username, name, grade, section, email, contact):
        """Update user profile"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users SET name=?, grade=?, section=?, email=?, contact=? WHERE username=?
            """, (name, grade, section, email, contact, username))
            conn.commit()
    
    @staticmethod
    def set_force_logout(username, value):
        """Set force logout flag"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("UPDATE users SET force_logout = ? WHERE username=?", (value, username))
            conn.commit()
    
    @staticmethod
    def check_force_logout(username):
        """Check if user should be force logged out"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("SELECT force_logout FROM users WHERE username=? AND role IN ('user','professor')", (username,))
            result = cur.fetchone()
            return result and result[0] == 1
    
    @staticmethod
    def update_account_info(user_id, username=None, name=None, grade=None, section=None):
        """Update account information (username, name, grade, section)"""
        updates = []
        params = []
        
        if username is not None:
            updates.append("username = ?")
            params.append(username)
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if grade is not None:
            updates.append("grade = ?")
            params.append(grade)
        if section is not None:
            updates.append("section = ?")
            params.append(section)
        
        if not updates:
            return
        
        params.append(user_id)
        
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
            conn.commit()
    
    @staticmethod
    def get_by_id(user_id):
        """Get user by ID"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT id, username, name, password, grade, section, role, created_at FROM users WHERE id=?", (user_id,))
            return cur.fetchone()
    
    @staticmethod
    def get_last_login(username):
        """Get last login timestamp"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'last_login' in columns:
                cur.execute("SELECT last_login FROM users WHERE username=?", (username,))
                result = cur.fetchone()
                return result[0] if result else None
            return None
    
    @staticmethod
    def get_failed_login_count(username):
        """Get failed login count"""
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(users)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'failed_login_count' in columns:
                cur.execute("SELECT failed_login_count FROM users WHERE username=?", (username,))
                result = cur.fetchone()
                return result[0] if result and result[0] else 0
            return 0

