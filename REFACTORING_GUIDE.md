# Application Structure Refactoring Guide

## Overview
The application has been refactored from a monolithic `app.py` file into a modular, organized structure following Flask best practices.

## New Structure

```
ComLabInventorySystem/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py             # Application configuration
│   ├── models/               # Database models
│   │   ├── __init__.py
│   │   ├── user.py           # User model and operations
│   │   ├── device.py         # Device model and operations
│   │   └── peripheral.py     # Peripheral model and operations
│   ├── routes/               # Route handlers (Blueprints)
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication routes (login, register, logout)
│   │   ├── admin.py          # Admin routes (dashboard, account management, labs)
│   │   ├── devices.py        # Device and inventory routes
│   │   └── api.py            # API endpoints
│   ├── services/             # Business logic services
│   │   ├── __init__.py
│   │   ├── device_monitor.py # Device monitoring service
│   │   └── alert_service.py  # Alert handling service
│   └── utils/                # Utility functions
│       ├── __init__.py
│       ├── helpers.py        # Helper functions
│       └── validators.py     # Validation functions
├── tests/                    # Test files (empty, ready for tests)
├── migrations/               # Database migrations (empty, ready for migrations)
├── logs/                     # Application logs directory
├── templates/                # HTML templates (unchanged)
├── static/                   # Static files (unchanged)
├── run.py                    # Application entry point (NEW)
└── app.py                    # OLD file (can be removed after verification)

```

## Key Changes

### 1. Application Entry Point
- **Old**: Run `python app.py`
- **New**: Run `python run.py` or `flask run`

### 2. Configuration
- Configuration moved to `app/config.py`
- Uses environment variables for sensitive data
- Centralized database and upload folder paths

### 3. Models
- Database operations separated into model classes:
  - `User`: User management operations
  - `Device`: Device management operations
  - `Peripheral`: Peripheral management operations

### 4. Routes (Blueprints)
- Routes organized by functionality:
  - `auth.py`: Authentication (login, register, logout)
  - `admin.py`: Admin functionality
  - `devices.py`: Device and inventory management
  - `api.py`: All API endpoints

### 5. Services
- Business logic separated from routes:
  - `device_monitor.py`: Device monitoring functionality
  - `alert_service.py`: Alert processing and management

### 6. Utils
- Reusable utility functions:
  - `helpers.py`: File handling, timestamps, hostname
  - `validators.py`: Input validation functions

## Migration Steps

1. **Backup your current `app.py`** (it's been kept for reference)

2. **Test the new structure**:
   ```bash
   python run.py
   ```

3. **Verify all routes work correctly**

4. **Once verified, you can remove the old `app.py` file**

## Benefits

1. **Better Organization**: Code is organized by functionality
2. **Maintainability**: Easier to find and modify specific features
3. **Testability**: Each module can be tested independently
4. **Scalability**: Easy to add new features without cluttering
5. **Best Practices**: Follows Flask application factory pattern

## Running the Application

```bash
# From ComLabInventorySystem directory
python run.py

# Or using Flask CLI
flask run
```

## Adding New Features

### Adding a New Route
1. Create or edit a file in `app/routes/`
2. Import and register the blueprint in `app/__init__.py`

### Adding a New Model
1. Create a new file in `app/models/`
2. Export it in `app/models/__init__.py`

### Adding a New Service
1. Create a new file in `app/services/`
2. Export it in `app/services/__init__.py`

## Notes

- All existing functionality has been preserved
- Database schema remains unchanged
- Templates and static files remain in their original locations
- The old `app.py` file is kept for reference but is no longer used

