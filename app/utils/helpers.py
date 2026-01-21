"""Helper utility functions"""
import os
import socket
import platform
import subprocess
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from app.config import Config


def allowed_file(filename):
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def get_hostname():
    """Get current hostname"""
    return socket.gethostname()


def get_current_timestamp():
    """Get current timestamp as formatted string"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def secure_filepath(filename):
    """Get secure filepath for uploads"""
    return os.path.join(Config.UPLOAD_FOLDER, secure_filename(filename))


def get_machine_guid():
    """Return machine GUID/UUID per platform."""
    system = platform.system()

    if system == "Windows":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                return guid
        except Exception:
            pass

    elif system == "Linux":
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        value = f.read().strip()
                        if value:
                            return value
                except Exception:
                    continue

    elif system == "Darwin":
        try:
            output = subprocess.check_output(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], text=True)
            match = re.search(r'"IOPlatformUUID"\s*=\s*"(.+?)"', output)
            if match:
                return match.group(1)
        except Exception:
            pass

    return None

