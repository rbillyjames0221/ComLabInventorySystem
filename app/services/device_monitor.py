"""Device monitoring service"""
from threading import Thread


def monitor_devices(username):
    """Monitors USB devices and prints connection/disconnection events."""
    print(f"\n🕵️ Monitoring USB/peripheral devices for user: {username}...")


def start_monitoring(username):
    """Start device monitoring in a separate thread"""
    Thread(target=monitor_devices, args=(username,), daemon=True).start()

