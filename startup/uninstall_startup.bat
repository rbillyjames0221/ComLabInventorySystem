@echo off
echo ====================================
echo ComLab Inventory System - Startup Uninstallation
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

echo Removing application from Windows startup...
cd /d "%~dp0.."
python startup\startup_service.py remove

echo.
echo Removing startup shortcut...
set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SHORTCUT_PATH=%STARTUP_FOLDER%\ComLabInventorySystem.lnk

if exist "%SHORTCUT_PATH%" (
    del "%SHORTCUT_PATH%"
    echo Startup shortcut removed.
) else (
    echo Startup shortcut not found.
)

echo.
echo ====================================
echo Uninstallation Complete!
echo ====================================
echo.
pause

