"""Startup service for running dashboard on system startup and PC locking"""
import os
import sys
import subprocess
import time
import ctypes
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


class StartupService:
    """Service for managing startup and PC locking"""
    
    def __init__(self):
        self.app_path = Path(__file__).parent.parent
        self.run_script = self.app_path / "run.py"
        self.lock_script = self.app_path / "startup" / "pc_locker.py"
    
    def is_admin(self):
        """Check if running as administrator"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    def add_to_startup(self):
        """Add application to Windows startup"""
        if not WIN32_AVAILABLE:
            print("Windows API not available. Cannot add to startup.")
            return False
        
        if not self.is_admin():
            print("Administrator privileges required to add to startup.")
            return False
        
        try:
            # Get startup folder path
            startup_folder = os.path.join(
                os.environ.get('APPDATA'),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
            )
            
            # Create shortcut
            shortcut_path = os.path.join(startup_folder, 'ComLabInventorySystem.lnk')
            
            # Create VBScript to create shortcut
            vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{sys.executable}"
oLink.Arguments = '"{self.run_script}"'
oLink.WorkingDirectory = "{self.app_path}"
oLink.Description = "ComLab Inventory System"
oLink.Save
'''
            
            # Write and execute VBScript
            vbs_file = os.path.join(self.app_path, 'startup', 'create_shortcut.vbs')
            with open(vbs_file, 'w') as f:
                f.write(vbs_script)
            
            subprocess.run(['cscript', '//nologo', vbs_file], check=True)
            os.remove(vbs_file)
            
            print("Application added to startup successfully.")
            return True
        except Exception as e:
            print(f"Error adding to startup: {e}")
            return False
    
    def remove_from_startup(self):
        """Remove application from Windows startup"""
        try:
            startup_folder = os.path.join(
                os.environ.get('APPDATA'),
                'Microsoft', 'Windows', 'Start Menu', 'Programs', 'Startup'
            )
            shortcut_path = os.path.join(startup_folder, 'ComLabInventorySystem.lnk')
            
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                print("Application removed from startup.")
                return True
            else:
                print("Startup shortcut not found.")
                return False
        except Exception as e:
            print(f"Error removing from startup: {e}")
            return False


if __name__ == "__main__":
    service = StartupService()
    if len(sys.argv) > 1:
        if sys.argv[1] == "add":
            service.add_to_startup()
        elif sys.argv[1] == "remove":
            service.remove_from_startup()
    else:
        print("Usage: python startup_service.py [add|remove]")


