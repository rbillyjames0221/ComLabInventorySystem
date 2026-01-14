"""Validation utility functions"""
import sqlite3
from app.config import Config


def validate_username_exists(username):
    """Check if username already exists in database"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE username = ?", (username,))
        return cur.fetchone() is not None


def validate_device_exists(tag=None, hostname=None, unique_id=None):
    """Check if device already exists by tag, hostname, or unique_id"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        # Check if unique_id column exists
        cur.execute("PRAGMA table_info(devices)")
        columns = [row[1] for row in cur.fetchall()]
        has_unique_id = "unique_id" in columns
        
        # Build query based on available parameters
        conditions = []
        params = []
        
        if tag:
            conditions.append("tag = ?")
            params.append(tag)
        
        if hostname:
            conditions.append("hostname = ?")
            params.append(hostname)
        
        if unique_id and has_unique_id:
            conditions.append("unique_id = ?")
            params.append(unique_id)
        
        if not conditions:
            return None
        
        query = f"SELECT comlab_id FROM devices WHERE {' OR '.join(conditions)}"
        cur.execute(query, params)
        return cur.fetchone()


def validate_peripheral_exists(assigned_pc, name):
    """Check if peripheral already exists for a PC"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM peripherals WHERE assigned_pc = ? AND name = ?", (assigned_pc, name))
        return cur.fetchone() is not None


def validate_lab_exists(lab_name):
    """Check if lab name already exists"""
    with sqlite3.connect(Config.DB_FILE) as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM labs WHERE LOWER(name) = LOWER(?)", (lab_name,))
        return cur.fetchone() is not None

