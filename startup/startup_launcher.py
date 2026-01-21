"""Startup launcher - combines PC locker and background device detector"""
import os
import sys
import time
import threading
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def start_flask_app():
    """Start Flask application"""
    try:
        from app import create_app
        app = create_app()
        
        # Run Flask app
        app.run(debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Error starting Flask app: {e}")


def start_pc_locker():
    """Start PC locker"""
    try:
        from startup.pc_locker import PCLocker
        locker = PCLocker()
        locker.start()
    except Exception as e:
        print(f"Error starting PC locker: {e}")


def start_background_detector():
    """Start background device detector"""
    try:
        from startup.background_device_detector import BackgroundDeviceDetector
        detector = BackgroundDeviceDetector()
        detector.start()
    except Exception as e:
        print(f"Error starting background detector: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("ComLab Inventory System - Startup Launcher")
    print("=" * 60)
    print("Starting services...")
    print()
    
    # Start Flask app in a thread
    flask_thread = threading.Thread(target=start_flask_app, daemon=True)
    flask_thread.start()
    
    # Wait a bit for Flask to start
    time.sleep(3)
    
    # Start background device detector in a thread
    detector_thread = threading.Thread(target=start_background_detector, daemon=True)
    detector_thread.start()
    
    # Start PC locker (this will block)
    print("Starting PC locker...")
    start_pc_locker()


