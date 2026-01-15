"""Background device detector - runs before login"""
import os
import sys
import time
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class BackgroundDeviceDetector:
    """Background device detector that runs before login"""
    
    def __init__(self):
        self.running = False
        self.check_interval = 10  # Check every 10 seconds
        
    def detect_devices(self):
        """Detect connected devices"""
        try:
            import platform
            if platform.system() != "Windows":
                return []
            
            from app.utils.device_detector import get_connected_devices, WIN32_AVAILABLE, IS_WINDOWS
            
            if not IS_WINDOWS or not WIN32_AVAILABLE:
                return []
            
            devices = get_connected_devices()
            return devices
        except Exception as e:
            print(f"Error detecting devices: {e}")
            return []
    
    def log_device_event(self, event_type, device_info):
        """Log device event to database"""
        try:
            import sqlite3
            from app.config import Config
            from app.utils.helpers import get_current_timestamp, get_hostname
            
            timestamp = get_current_timestamp()
            hostname = get_hostname()
            
            with sqlite3.connect(Config.DB_FILE) as conn:
                cur = conn.cursor()
                
                # Check if peripheral_logs table exists
                cur.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='peripheral_logs'
                """)
                if not cur.fetchone():
                    # Create table if it doesn't exist
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS peripheral_logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            unique_id TEXT,
                            event_type TEXT,
                            device_type TEXT,
                            timestamp TEXT,
                            device_name TEXT
                        )
                    """)
                
                # Log the event
                cur.execute("""
                    INSERT INTO peripheral_logs 
                    (unique_id, event_type, device_type, timestamp, device_name)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    device_info.get('unique_id', ''),
                    event_type,
                    device_info.get('type', 'Unknown'),
                    timestamp,
                    hostname
                ))
                conn.commit()
        except Exception as e:
            print(f"Error logging device event: {e}")
    
    def monitor_devices(self):
        """Monitor devices in background"""
        previous_devices = {}
        
        while self.running:
            try:
                current_devices = self.detect_devices()
                current_device_ids = {dev.get('unique_id', ''): dev for dev in current_devices if dev.get('unique_id')}
                
                # Detect newly connected devices
                for device_id, device_info in current_device_ids.items():
                    if device_id not in previous_devices:
                        self.log_device_event('connected', device_info)
                        print(f"Device connected: {device_info.get('name', 'Unknown')}")
                
                # Detect disconnected devices
                for device_id, device_info in previous_devices.items():
                    if device_id not in current_device_ids:
                        self.log_device_event('disconnected', device_info)
                        print(f"Device disconnected: {device_info.get('name', 'Unknown')}")
                
                previous_devices = current_device_ids
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in monitor_devices: {e}")
                time.sleep(self.check_interval)
    
    def start(self):
        """Start background device detection"""
        self.running = True
        monitor_thread = threading.Thread(target=self.monitor_devices, daemon=True)
        monitor_thread.start()
        print("Background device detector started.")
        
        # Keep main thread alive
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nStopping background device detector...")
            self.running = False


if __name__ == "__main__":
    detector = BackgroundDeviceDetector()
    detector.start()

