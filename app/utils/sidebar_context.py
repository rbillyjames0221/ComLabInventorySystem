"""Sidebar context helper"""
import sqlite3
from flask import session
from app.config import Config


def get_sidebar_context(current_page=None, comlab_id=None):
    """Get sidebar context variables for templates"""
    context = {
        'current_page': current_page,
        'comlab_id': comlab_id,
        'labs': [],
        'pending_accounts_count': 0,
        'pending_edits_count': 0,
        'alerts_count': 0
    }
    
    # Get user info from session
    username = session.get('username')
    role = session.get('role')
    
    if not username or not role:
        return context
    
    # Create a simple user object for templates
    context['current_user'] = {
        'username': username,
        'role': role
    }
    
    # If admin, get labs and pending counts
    if role == 'admin':
        with sqlite3.connect(Config.DB_FILE) as conn:
            cur = conn.cursor()
            
            # Get labs
            cur.execute("SELECT id, name FROM labs ORDER BY id ASC")
            context['labs'] = cur.fetchall()
            
            # Get pending accounts count
            cur.execute("SELECT COUNT(*) FROM users WHERE status='pending'")
            context['pending_accounts_count'] = cur.fetchone()[0] or 0
            
            # Get pending profile edits count
            try:
                cur.execute("SELECT COUNT(*) FROM profile_edits_pending WHERE status='pending'")
                context['pending_edits_count'] = cur.fetchone()[0] or 0
            except sqlite3.OperationalError:
                # Table might not exist
                context['pending_edits_count'] = 0
            
            # Get active alerts count (faulty, missing, replaced devices)
            try:
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM peripheral_alerts 
                    WHERE deleted = 0 
                    AND alert_type IN ('faulty', 'missing', 'replaced')
                """)
                context['alerts_count'] = cur.fetchone()[0] or 0
            except sqlite3.OperationalError:
                # Table might not exist
                context['alerts_count'] = 0
    
    return context

