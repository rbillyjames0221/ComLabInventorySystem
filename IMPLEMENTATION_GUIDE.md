# ComLab Inventory System - Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [Database Migration](#database-migration)
4. [Status Management System](#status-management-system)
5. [Password Reset Flow](#password-reset-flow)
6. [Startup Integration & PC Locking](#startup-integration--pc-locking)
7. [Background Device Detection](#background-device-detection)
8. [Admin Settings](#admin-settings)
9. [Production Deployment](#production-deployment)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide covers the implementation of all new features and improvements to the ComLab Inventory System, including:

- **Status Management**: Manual status updates for Missing, Replaced, and Faulty devices
- **Password Reset Flow**: Admin-initiated password reset with first-login prompt
- **Startup Integration**: Automatic startup and PC locking until login
- **Background Device Detection**: Device monitoring before user login
- **Admin Settings**: System configuration and audit logging
- **Production Readiness**: Error handling, logging, and database improvements

---

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11 (for PC locking and device detection features)
- Administrator privileges (for startup installation)

### Step 1: Install Dependencies

```bash
cd ComLabInventorySystem
pip install -r requirements.txt
```

### Step 2: Run Database Migration

```bash
python migrations/add_status_management.py
```

This will create:
- `peripheral_status_history` table
- `system_settings` table
- `audit_log` table
- Additional columns in `peripherals` and `users` tables
- Database indexes for performance

---

## Database Migration

### Manual Migration

If the migration script doesn't run automatically, you can manually execute the SQL:

```sql
-- Create status history table
CREATE TABLE IF NOT EXISTS peripheral_status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peripheral_id INTEGER NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    reason TEXT,
    updated_by TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (peripheral_id) REFERENCES peripherals(id)
);

-- Add columns to peripherals table
ALTER TABLE peripherals ADD COLUMN status_updated_by TEXT;
ALTER TABLE peripherals ADD COLUMN status_updated_at TEXT;
ALTER TABLE peripherals ADD COLUMN status_reason TEXT;

-- Add columns to users table
ALTER TABLE users ADD COLUMN password_reset_required INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN password_reset_by TEXT;
ALTER TABLE users ADD COLUMN password_reset_at TEXT;

-- Create system_settings table
CREATE TABLE IF NOT EXISTS system_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT UNIQUE NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_by TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT,
    resource_id INTEGER,
    details TEXT,
    ip_address TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_peripheral_status ON peripherals(status, lab_id);
CREATE INDEX IF NOT EXISTS idx_peripheral_unique_id ON peripherals(unique_id);
CREATE INDEX IF NOT EXISTS idx_device_comlab_tag ON devices(comlab_id, tag);
CREATE INDEX IF NOT EXISTS idx_alerts_location_deleted ON peripheral_alerts(location, deleted, alert_type);
CREATE INDEX IF NOT EXISTS idx_status_history_peripheral ON peripheral_status_history(peripheral_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_log(user_id, action);
```

---

## Status Management System

### Features
- Manual status updates by admins
- Status history tracking
- Status transition validation
- Automatic alert creation for Missing, Faulty, and Replaced statuses

### Usage

#### Admin Interface
1. Navigate to Inventory page (`/comlab/<lab_id>/inventory`)
2. Click the status edit button (pencil icon) next to any peripheral status
3. Select new status from dropdown
4. Optionally add a reason
5. Click Save

#### API Endpoints

**Update Status:**
```http
POST /api/update_peripheral_status
Content-Type: application/json

{
    "peripheral_id": 123,
    "status": "missing",
    "reason": "Device not found during inspection"
}
```

**Get Status History:**
```http
GET /api/get_status_history/<peripheral_id>
```

**Bulk Update Status:**
```http
POST /api/bulk_update_status
Content-Type: application/json

{
    "peripheral_ids": [123, 124, 125],
    "status": "faulty",
    "reason": "Batch inspection"
}
```

### Status Values
- `connected`: Device is connected and working
- `unplugged`: Device is disconnected
- `missing`: Device is missing (triggers alert)
- `faulty`: Device is faulty (triggers alert)
- `replaced`: Device has been replaced (triggers alert)

### Status Transitions
Valid transitions are enforced:
- `connected` → `unplugged`, `faulty`, `replaced`
- `unplugged` → `connected`, `missing`, `faulty`
- `missing` → `connected`, `replaced`
- `faulty` → `connected`, `replaced`
- `replaced` → `connected`

---

## Password Reset Flow

### Admin Password Reset

1. Navigate to Account Management (`/account-management`)
2. Find the user whose password needs to be reset
3. Click "Reset Password"
4. Enter new temporary password
5. Enter admin password for confirmation
6. Click Reset

### User First Login

When a user logs in after admin password reset:

1. User enters username and temporary password
2. System detects `password_reset_required` flag
3. User is redirected to `/change_password_first_login`
4. User must set a new password (minimum 8 characters)
5. After password change, user can access dashboard

### Implementation Details

- Admin password reset sets `password_reset_required = 1` in users table
- Login route checks this flag and redirects to password change page
- Password change page blocks access to dashboard until password is changed
- After password change, flag is cleared automatically

---

## Startup Integration & PC Locking

### Installation

**Option 1: Using Batch Script (Recommended)**
1. Right-click `startup/install_startup.bat`
2. Select "Run as administrator"
3. Follow prompts

**Option 2: Manual Installation**
```bash
cd ComLabInventorySystem
python startup/startup_service.py add
```

### How It Works

1. **Startup Launcher** (`startup_launcher.py`):
   - Starts Flask application
   - Starts background device detector
   - Starts PC locker

2. **PC Locker** (`pc_locker.py`):
   - Locks desktop by disabling explorer.exe
   - Shows fullscreen browser with login page
   - Monitors login status every 5 seconds
   - Unlocks desktop when user logs in
   - Re-locks when user logs out

3. **Background Device Detector** (`background_device_detector.py`):
   - Detects USB devices before login
   - Logs device events to database
   - Runs continuously in background

### Uninstallation

```bash
python startup/startup_service.py remove
```

Or use:
```bash
startup/uninstall_startup.bat
```

### Configuration

Edit `startup/pc_locker.py` to adjust:
- `check_interval`: How often to check login status (default: 5 seconds)
- Lock/unlock behavior

---

## Background Device Detection

### Features
- Detects USB devices before user login
- Logs device connect/disconnect events
- Runs continuously in background
- Works independently of user session

### Implementation

The background detector:
1. Runs as a separate thread
2. Checks for devices every 10 seconds (configurable)
3. Compares current devices with previous state
4. Logs new connections and disconnections
5. Stores events in `peripheral_logs` table

### Logging Format

Events are logged with:
- `unique_id`: Device unique identifier
- `event_type`: `connected` or `disconnected`
- `device_type`: Device type (Mouse, Keyboard, etc.)
- `timestamp`: Event timestamp
- `device_name`: PC hostname/tag

---

## Admin Settings

### Access
Navigate to `/admin/settings` (admin only)

### Available Settings

1. **System Name**: Display name for the system
2. **Session Timeout**: Session timeout in minutes (default: 480)
3. **Device Check Interval**: How often to check devices in seconds (default: 10)

### Audit Logs

View audit logs in Admin Settings page:
- User actions
- Status changes
- Settings updates
- System events

Logs include:
- Timestamp
- User ID
- Action type
- Details
- IP Address

---

## Production Deployment

### 1. Environment Setup

Create `.env` file:
```env
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
DB_FILE=database.db
```

### 2. Logging Configuration

Logs are automatically configured:
- Location: `logs/app.log`
- Rotation: 10MB per file, 10 backups
- Format: Timestamp, Level, Message, File, Line

### 3. Error Handling

Global error handlers are configured for:
- 404 Not Found
- 500 Internal Server Error
- Database errors
- Validation errors

### 4. Security

- CSRF protection enabled (Flask-WTF)
- Rate limiting on API endpoints
- Session security configured
- Input validation on all forms

### 5. Database Backup

Set up automated backups:
```bash
# Windows Task Scheduler
# Run daily: python backup_db.py
```

### 6. Startup Installation

For production deployment:
1. Install startup service (see Startup Integration section)
2. Configure firewall rules
3. Set up SSL certificate (recommended)
4. Configure reverse proxy (optional)

---

## Troubleshooting

### Database Migration Issues

**Error: "database is locked"**
- Stop Flask server
- Close any database viewers
- Run migration again

**Error: "table already exists"**
- Migration already completed
- Safe to ignore

### Startup Issues

**PC Locker not working**
- Ensure running as administrator
- Check Windows API availability (`pywin32` installed)
- Verify explorer.exe can be killed/restarted

**Background detector not running**
- Check logs in `logs/app.log`
- Verify `pywin32` is installed
- Check Windows permissions

### Status Management Issues

**Status not updating**
- Check user has admin role
- Verify API endpoint is accessible
- Check browser console for errors
- Verify database migration completed

### Password Reset Issues

**User not prompted to change password**
- Check `password_reset_required` flag in database
- Verify login route is checking flag
- Check session is being set correctly

---

## API Reference

### Status Management

**Update Status**
- `POST /api/update_peripheral_status`
- Requires: `peripheral_id`, `status`
- Optional: `reason`

**Get Status History**
- `GET /api/get_status_history/<peripheral_id>`
- Returns: Array of status history entries

**Bulk Update**
- `POST /api/bulk_update_status`
- Requires: `peripheral_ids[]`, `status`
- Optional: `reason`

### Settings

**Get Settings**
- `GET /api/settings`
- Returns: All system settings

**Update Setting**
- `POST /api/settings`
- Requires: `setting_key`, `setting_value`
- Optional: `description`

**Get Audit Logs**
- `GET /api/audit_logs`
- Optional params: `user_id`, `action`, `limit`

---

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Review audit logs in Admin Settings
3. Check database for data integrity
4. Verify all migrations completed

---

## Version History

### Version 2.0 (Current)
- Status Management System
- Password Reset Flow
- Startup Integration
- Background Device Detection
- Admin Settings
- Production Readiness Improvements

### Version 1.0
- Initial release
- Basic inventory management
- User authentication
- Device registration

