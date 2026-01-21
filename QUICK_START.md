# Quick Start Guide - ComLab Inventory System

## Installation Steps

### 1. Install Dependencies
```bash
cd ComLabInventorySystem
pip install -r ../requirements.txt
```

### 2. Run Database Migration
```bash
python migrations/add_status_management.py
```

### 3. Start the Application
```bash
python run.py
```

The application will be available at `http://localhost:5000`

## New Features

### Status Management
- Admins can manually set device status to Missing, Replaced, or Faulty
- Status changes are tracked in history
- Access via Inventory page → Click status edit button

### Password Reset Flow
- Admin resets password → User must change on first login
- No password format restrictions for admin reset
- User must set new password (min 8 chars) before accessing dashboard

### Startup Integration (Optional)
To enable PC locking and auto-startup:
```bash
# Run as Administrator
startup/install_startup.bat
```

This will:
- Lock PC until user logs in
- Start application on system boot
- Run background device detection

### Admin Settings
- Access: `/admin/settings`
- Configure system settings
- View audit logs

## Testing

### Test Status Management
1. Login as admin
2. Go to Inventory page
3. Click status edit button (pencil icon)
4. Change status to "Missing"
5. Add reason (optional)
6. Save

### Test Password Reset
1. Login as admin
2. Go to Account Management
3. Reset a user's password
4. Logout
5. Login as that user
6. Should be prompted to change password

## Troubleshooting

**Database locked error:**
- Stop Flask server (Ctrl+C)
- Close any database viewers
- Run migration again

**Startup not working:**
- Ensure running as Administrator
- Check `pywin32` is installed: `pip install pywin32`

**Status not updating:**
- Check browser console for errors
- Verify admin role
- Check database migration completed

For detailed documentation, see `IMPLEMENTATION_GUIDE.md`


