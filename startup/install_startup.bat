@echo off
echo ====================================
echo ComLab Inventory System - Startup Installation
echo ====================================
echo.

REM Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo Step 1: Adding application to Windows startup...
cd /d "%~dp0.."
python startup\startup_service.py add

echo.
echo Step 2: Creating startup launcher shortcut...
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\ComLabInventorySystem.lnk

REM Create shortcut using PowerShell
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = 'python'; $Shortcut.Arguments = '%~dp0startup\startup_launcher.py'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.Description = 'ComLab Inventory System'; $Shortcut.Save()"

echo.
echo ====================================
echo Installation Complete!
echo ====================================
echo.
echo The application will now start automatically on system boot.
echo The PC will be locked until a user logs in.
echo.
pause


