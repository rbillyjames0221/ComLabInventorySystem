"""PC Locker - Restricts PC usage until user logs in"""
import os
import sys
import time
import ctypes
import subprocess
import threading
from pathlib import Path

# Windows-specific imports
try:
    import win32api
    import win32con
    import win32gui
    import win32process
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class PCLocker:
    """PC Locker that restricts PC usage until login"""
    
    def __init__(self):
        self.app_path = Path(__file__).parent.parent
        self.locked = True
        self.check_interval = 5  # Check every 5 seconds
        
    def is_admin(self):
        """Check if running as administrator"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def lock_desktop(self):
        """Lock the desktop by disabling explorer and showing fullscreen browser"""
        if not WIN32_AVAILABLE:
            print("Windows API not available. Cannot lock desktop.")
            return False
        
        try:
            # Kill explorer.exe to disable desktop
            subprocess.run(['taskkill', '/F', '/IM', 'explorer.exe'], 
                         capture_output=True, timeout=5)
            print("Desktop locked.")
            return True
        except Exception as e:
            print(f"Error locking desktop: {e}")
            return False
    
    def unlock_desktop(self):
        """Unlock the desktop by restarting explorer"""
        if not WIN32_AVAILABLE:
            return False
        
        try:
            # Restart explorer.exe
            subprocess.Popen('explorer.exe', shell=True)
            print("Desktop unlocked.")
            return True
        except Exception as e:
            print(f"Error unlocking desktop: {e}")
            return False
    
    def check_login_status(self):
        """Check if user is logged in by checking active_sessions table"""
        try:
            import sqlite3
            from app.config import Config
            from app.utils.helpers import get_hostname
            
            hostname = get_hostname()
            
            with sqlite3.connect(Config.DB_FILE) as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT student_id FROM active_sessions 
                    WHERE pc_tag = ? OR pc_tag = ?
                """, (hostname, hostname))
                result = cur.fetchone()
                
                return result is not None
        except Exception as e:
            print(f"Error checking login status: {e}")
            return False
    
    def start_browser_fullscreen(self):
        """Start browser in fullscreen kiosk mode"""
        try:
            import webbrowser
            import socket
            
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            url = f"http://{local_ip}:5000"
            
            # Open in default browser (will be fullscreen)
            webbrowser.open(url)
            
            # Try to make it fullscreen using Windows API
            if WIN32_AVAILABLE:
                time.sleep(2)  # Wait for browser to open
                # Find browser window and maximize
                def enum_handler(hwnd, ctx):
                    if win32gui.IsWindowVisible(hwnd):
                        title = win32gui.GetWindowText(hwnd)
                        if "ComLab" in title or "localhost" in title or "127.0.0.1" in title:
                            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                            win32gui.SetForegroundWindow(hwnd)
                
                win32gui.EnumWindows(enum_handler, None)
            
            return True
        except Exception as e:
            print(f"Error starting browser: {e}")
            return False
    
    def monitor_login(self):
        """Monitor login status and lock/unlock accordingly"""
        while True:
            try:
                logged_in = self.check_login_status()
                
                if logged_in and self.locked:
                    # User logged in - unlock desktop
                    self.unlock_desktop()
                    self.locked = False
                    print("User logged in. Desktop unlocked.")
                elif not logged_in and not self.locked:
                    # User logged out - lock desktop
                    self.lock_desktop()
                    self.start_browser_fullscreen()
                    self.locked = True
                    print("User logged out. Desktop locked.")
                
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in monitor_login: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """Start the PC locker"""
        if not self.is_admin():
            print("Warning: Administrator privileges recommended for PC locking.")
        
        # Lock desktop initially
        self.lock_desktop()
        
        # Start browser
        self.start_browser_fullscreen()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_login, daemon=True)
        monitor_thread.start()
        
        print("PC Locker started. Desktop is locked until user logs in.")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping PC Locker...")
            self.unlock_desktop()


if __name__ == "__main__":
    locker = PCLocker()
    locker.start()

