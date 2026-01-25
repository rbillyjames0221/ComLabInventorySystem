# 🖥️ ComLab Inventory System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-10%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**A comprehensive computer laboratory inventory management system with real-time peripheral detection, user session tracking, and automated device monitoring.**

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Screenshots](#-screenshots) • [Contributing](#-contributing)

</div>

---

## 📋 Overview

ComLab Inventory System is a Flask-based web application designed for educational institutions to manage computer laboratory assets efficiently. It provides real-time tracking of computers, peripherals (mice, keyboards, monitors, etc.), and user sessions across multiple labs.

### Key Capabilities

- 🔍 **Real-time Device Detection** - Automatically detects USB peripherals connected to Windows PCs
- 👥 **Multi-role User Management** - Support for admins, professors, and students
- 📊 **Comprehensive Reporting** - Track device status, anomalies, and generate reports
- 🔐 **Security Features** - Rate limiting, CSRF protection, account lockout, and audit logging
- 🖥️ **PC Locking** - Optional startup integration to lock PCs until user login

---

## ✨ Features

### Device & Inventory Management
- **Multi-lab Support** - Manage multiple computer laboratories from a single dashboard
- **Device Registration** - Register PCs via secure token-based links
- **Peripheral Tracking** - Track mice, keyboards, monitors, webcams, speakers, and more
- **Status Management** - Mark devices as Connected, Unplugged, Missing, Faulty, or Replaced
- **Unregistered Device Detection** - Automatically detect and flag unauthorized devices

### User Management
- **Role-based Access Control** - Admin, Professor, and Student roles with different permissions
- **Account Approval Workflow** - New registrations require admin approval
- **Password Reset Flow** - Admin-initiated password reset with mandatory change on first login
- **Profile Management** - Users can update profiles with admin approval
- **Session Tracking** - Track active user sessions across all PCs

### Security & Monitoring
- **Rate Limiting** - Protect against brute force attacks (5 attempts per 15 minutes)
- **Account Lockout** - Automatic 30-minute lockout after 5 failed login attempts
- **CSRF Protection** - All forms protected against cross-site request forgery
- **Audit Logging** - Track all administrative actions
- **Session Security** - Secure cookie configuration with configurable timeout

### Alerts & Reporting
- **Automated Alerts** - Generate alerts for missing, faulty, or replaced devices
- **Status History** - Track all status changes with timestamps and reasons
- **Summary Dashboard** - View statistics by lab, device type, and date range
- **Export Reports** - Generate reports for inventory audits

### Windows Integration (Optional)
- **Startup Service** - Auto-start application on system boot
- **PC Locking** - Lock desktop until user authenticates
- **Background Detection** - Monitor device connections before user login

---

## 🔧 Installation

### Prerequisites

- **Python 3.8+** - [Download Python](https://www.python.org/downloads/)
- **Windows 10/11** - Required for device detection features (optional for basic functionality)
- **Administrator privileges** - Required for startup integration (optional)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/ComLabInventorySystem.git
cd ComLabInventorySystem
```

### Step 2: Create Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies include:**
- Flask >= 2.3.0
- Flask-Limiter >= 3.5.0
- Flask-WTF >= 1.2.0
- Pillow >= 10.0.0
- Werkzeug >= 3.0.0
- pywin32 >= 306 (Windows only)
- WMI >= 1.5.1 (Windows only)
- python-dotenv >= 1.0.0

### Step 4: Initialize Database

```bash
python setup_db.py
python migrations/add_status_management.py
```

### Step 5: Run the Application

```bash
python run.py
```

The application will be available at `http://localhost:5000`

---

## 🚀 Quick Start

### 1. First-time Setup

1. Navigate to `http://localhost:5000`
2. Click "Create Account" to register an admin account
3. Wait for account approval (first admin is auto-approved)
4. Login with your credentials

### 2. Add a Computer Lab

1. Go to Admin Dashboard
2. Click "Add Lab"
3. Enter lab name (e.g., "Computer Lab 1")

### 3. Register PCs

1. From Admin Dashboard, click on a lab
2. Click "Generate Registration Link"
3. Open the link on the target PC
4. Fill in PC details and submit

### 4. View Inventory

1. Click on a lab from the dashboard
2. View all registered PCs and their peripherals
3. Click on a PC to see detailed peripheral information

---

## 📖 Documentation

### Project Structure

```
ComLabInventorySystem/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration settings
│   ├── models/              # Database models
│   │   ├── device.py        # PC/Device model
│   │   ├── peripheral.py    # Peripheral model
│   │   ├── user.py          # User model
│   │   ├── status_history.py
│   │   └── system_settings.py
│   ├── routes/              # Route blueprints
│   │   ├── admin.py         # Admin routes
│   │   ├── api.py           # API endpoints
│   │   ├── auth.py          # Authentication routes
│   │   └── devices.py       # Device/inventory routes
│   ├── services/            # Business logic
│   │   ├── alert_service.py
│   │   ├── device_monitor.py
│   │   └── status_service.py
│   └── utils/               # Utility functions
│       ├── auth_decorators.py
│       ├── device_detector.py
│       ├── security.py
│       └── validators.py
├── migrations/              # Database migrations
├── startup/                 # Windows startup integration
│   ├── install_startup.bat
│   ├── pc_locker.py
│   └── startup_service.py
├── static/                  # CSS, JS, images
├── templates/               # Jinja2 templates
├── logs/                    # Application logs
├── run.py                   # Application entry point
├── setup_db.py              # Database initialization
└── requirements.txt         # Python dependencies
```

### 🧭 Dashboard Pages & Related Files

Beginner-friendly navigation starts with understanding the **route → template → static asset** chain for each dashboard. Here are the key UI components, their routes, and any files that tie them together.

#### Admin experience
- **Route files:** `app/routes/admin.py` (blueprint `admin_bp`)
- **Templates:** `templates/admin_dashboard.html`, `templates/account_management.html`, `templates/admin_users.html`, `templates/admin_settings.html`
- **Purpose:** `/admin` lists labs and supports inline editing (toggle `?edit=1` to enter edit mode). `/account-management` paginates active users by role while the settings page lets admins update `SystemSettings` values.
- **Supporting files:** `templates/includes/sidebar.html` + `templates/includes/topbar.html` inject shared navigation; `static/css/sidebar.css` + `static/css/responsive.css` style the layout; `static/js/sidebar.js` + `static/js/topbar-menu.js` handle collapsible menus and dropdown toggles.
- **Beginner tip:** When the dashboard needs to add a lab, the JavaScript posts to `/admin/add_lab`, `/rename_lab`, or `/remove_lab`. Changes to labs are simply writes to the `labs` table via SQLite, so follow the pattern in `admin.py` to keep forms consistent.

#### Inventory and peripheral management
- **Route files:** `app/routes/devices.py` (blueprint `devices_bp`)
- **Main template:** `templates/inventory.html` used by `/comlab/<lab_id>/inventory`
  - Renders every PC (`Device.get_by_location`) plus peripherals grouped by PC tag (`Peripheral.get_by_lab`).
  - Pulls `lab_name` from the `labs` table so the header shows the friendly lab name.
- **Supporting dashboards:** `/inventory/peripheral` → `templates/peripheral_summary.html`, `/inventory/view_alerts` → `templates/view_alerts.html`, `/inventory/view_summary` → `templates/view_summary.html`, `/inventory/display_usb_devices` → `templates/usb_devices.html`, `/inventory/view_reports` → `templates/view_reports.html`. Alias routes (like `/comlab/<lab_id>/devices`) redirect to these views for backward compatibility.
- **Static helpers:** `static/js/alerts.js` updates alert badges, and `static/js/client_device_detection.js` supplies device fingerprints for registration. Every template includes the sidebar/topbar partials, so new dashboards inherit navigation automatically.
- **Beginner tip:** Follow one Flask view from SQL query → `dict(row)` conversion → `render_template`. That flow shows how data is exposed to Jinja and where to add new fields. For example, to display a new peripheral column, edit `templates/inventory.html` and update the dictionary keys sent from `comlab_inventory()`.

#### Student dashboard
- **Route file:** `app/routes/devices.py`
- **Template:** `templates/student_dashboard.html`
- **Features:** Displays the logged-in student’s profile (`User.get_profile`), current PC/peripheral pairings and anomalies, emergency logout requests, and forms to upload avatars or change passwords. Peripheral status auto-updates by calling `app.utils.device_detector.get_connected_devices()` when running on Windows.
- **Beginner tip:** The template shows how flash messages (success, error) surface after POST actions such as `/upload_profile` or `/change_password`. Trace `devices.py` to see how each POST handler wraps in a redirect back to `/student_dashboard`.

#### Registration & helper routes
- `/generate_link` + `/register_device/<token>` both render `templates/register_device.html`. The GET route shows a simple form (`static/js/login.js`) to generate tokens, while the POST route records devices and detected peripherals via `Device.create()` and `Peripheral.create()`.
- **Beginner tip:** Client detection helpers (`app.utils.client_device_detector`, `app.utils.helpers`) feed hidden fields to this form. If you add more metadata, update both the HTML form and the POST handler so Flask can access `request.form["your_field"]`.

#### Shared helpers
- **Navigation includes:** `templates/includes/sidebar.html` and `templates/includes/topbar.html` are reused across admin, inventory, and student dashboards. Edit them to add new menu items for any new route.
- **Global utils:** `app/utils/sidebar_context.py`, `helpers.py`, `validators.py`, and `constants.py` group shared logic like lab listing, device fingerprinting, or string validation. Reuse these helpers before writing new SQL or validation code.
- **Styles & scripts:** All dashboards pull `static/css/sidebar.css`, `static/css/login.css`, and the JS files mentioned earlier. When you create new templates, include the necessary CSS/JS by following the structure already present in `templates/includes/topbar.html`.

This breakdown helps beginners trace each dashboard from the HTTP request through the template rendering and static assets, making it easier to extend functionality step by step.

### API Endpoints

#### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/login` | User login |
| GET/POST | `/register` | User registration |
| GET | `/logout` | User logout |
| GET/POST | `/change_password_first_login` | Password change after reset |

#### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin` | Admin dashboard |
| GET | `/admin/settings` | System settings |
| GET | `/account-management` | User management |
| POST | `/add_lab` | Create new lab |
| POST | `/api/create_account` | Create user account |
| POST | `/api/reset_password/<user_id>` | Reset user password |

#### Devices & Inventory
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/comlab/<lab_id>/inventory` | View lab inventory |
| GET | `/generate_link` | Generate device registration link |
| GET/POST | `/register_device/<token>` | Register a new PC |
| GET | `/student_dashboard` | Student dashboard |

#### Status Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/update_peripheral_status` | Update peripheral status |
| GET | `/api/get_status_history/<id>` | Get status history |
| POST | `/api/bulk_update_status` | Bulk status update |

### Configuration

Create a `.env` file in the root directory:

```env
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key-here
```

#### Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `FLASK_ENV` | development | Environment mode |
| `SECRET_KEY` | auto-generated | Session encryption key |
| `PERMANENT_SESSION_LIFETIME` | 28800 | Session timeout (seconds) |

### Status Values

| Status | Description | Triggers Alert |
|--------|-------------|----------------|
| `connected` | Device is connected and working | No |
| `unplugged` | Device is disconnected | No |
| `missing` | Device cannot be found | Yes |
| `faulty` | Device is malfunctioning | Yes |
| `replaced` | Device has been replaced | Yes |

### Valid Status Transitions

```
connected → unplugged, faulty, replaced
unplugged → connected, missing, faulty
missing → connected, replaced
faulty → connected, replaced
replaced → connected
```

---

## 🖥️ Windows Startup Integration

### Installation

Run as Administrator:

```bash
startup\install_startup.bat
```

Or manually:

```bash
python startup/startup_service.py add
```

### Features

1. **Auto-start** - Application starts on Windows boot
2. **PC Locking** - Desktop is locked until user authenticates
3. **Background Detection** - Monitors devices before login

### Uninstallation

```bash
startup\uninstall_startup.bat
```

Or:

```bash
python startup/startup_service.py remove
```

---

## 🔒 Security Features

### Rate Limiting
- Login: 5 attempts per 15 minutes
- API: 200 requests per day, 50 per hour

### Account Protection
- Automatic lockout after 5 failed attempts
- 30-minute lockout duration
- Login attempts are logged

### Session Security
- HTTP-only cookies
- SameSite cookie policy
- Secure cookies in production (HTTPS)
- Configurable session timeout

### Audit Logging
All administrative actions are logged:
- User management operations
- Settings changes
- Status updates
- Login attempts

---

## 🐛 Troubleshooting

### Database Issues

**Error: "database is locked"**
```bash
# Stop Flask server (Ctrl+C)
# Close any database viewers
# Restart the application
python run.py
```

**Error: "table already exists"**
- Migration already completed - safe to ignore

### Device Detection Issues

**Devices not detected**
- Ensure running on Windows 10/11
- Install pywin32: `pip install pywin32`
- Run as Administrator for full access

### Startup Issues

**PC Locker not working**
- Run as Administrator
- Verify pywin32 is installed
- Check Windows API availability

### Login Issues

**Account locked**
- Wait 30 minutes for automatic unlock
- Or ask admin to reset via database

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/ComLabInventorySystem.git
cd ComLabInventorySystem

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
set FLASK_ENV=development
python run.py
```

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Flask-WTF](https://flask-wtf.readthedocs.io/) - CSRF protection
- [Flask-Limiter](https://flask-limiter.readthedocs.io/) - Rate limiting
- [Pillow](https://pillow.readthedocs.io/) - Image processing
- [Font Awesome](https://fontawesome.com/) - Icons

---

## 📞 Support

For issues or questions:

1. Check the [Troubleshooting](#-troubleshooting) section
2. Review application logs in `logs/app.log`
3. Open an issue on GitHub

---

<div align="center">

**Made with ❤️ for Computer Laboratories**

[⬆ Back to Top](#️-comlab-inventory-system)

</div>


