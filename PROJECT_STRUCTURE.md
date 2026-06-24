PROJECT STRUCTURE & FILE MANIFEST

🚀 CoC Bot Server System

📂 Root Directory
├── 🔧 Configuration & Setup
│   ├── config.py                   Python config handler
│   ├── config.yaml                 Bot settings (loot, troops, delays)
│   ├── .env.example                Environment variables template
│   ├── .gitignore                  Git patterns (NEW)
│   ├── requirements.txt            Root dependencies
│   │
│   └── 📝 Documentation
│       ├── README.md               Original bot documentation
│       ├── DEPLOYMENT.md           Complete deployment guide (NEW)
│       ├── IMPLEMENTATION_COMPLETE.md  What was built (NEW)
│       ├── IMPLEMENTATION_SUMMARY.txt  Build statistics (NEW)
│       ├── QUICK_REFERENCE.py      Commands & routes (NEW)
│       └── INSTALLATION_SUMMARY.txt This file
│
├── 🤖 Bot Core (Original - Unchanged)
│   ├── main.py                     Entry point (GUI mode)
│   ├── bot_engine.py               Farming logic (core algorithm)
│   ├── bot_client.py               Desktop client (legacy)
│   ├── gui.py                      Desktop GUI (legacy)
│   ├── adb_controller.py           Android Debug Bridge integration
│   ├── vision.py                   Template matching
│   ├── troop_detector.py           Troop detection AI
│   ├── take_ss.py                  Screenshot utility
│   ├── zone_picker.py              UI zone picker
│   └── check_resolution.py         Resolution checker
│
├── 🚀 Bot Launcher (NEW)
│   └── bot_launcher.py             Web-triggered bot entry point
│       - Spawned by bot_executor
│       - Receives config as JSON
│       - Launches CoCBot process
│       - Logs to logs/bot_<device_id>.log
│
├── 🛠️ Setup Scripts (NEW)
│   ├── setup.py                    Automated environment setup
│   ├── run.bat                     Windows development runner
│   ├── run.sh                      Unix development runner
│   └── checklist.py                Pre-deployment validator
│
├── 🖼️ Assets (Original)
│   ├── troop_images/               Custom troop detection images
│   ├── templates/                  Game template images
│   └── *.png                       Screenshots/temp images
│
└── 📊 Logs (Auto-generated)
    └── logs/
        ├── bot.log                 Main bot log
        └── bot_*.log               Per-device execution logs

═══════════════════════════════════════════════════════════════

📂 server/ — Flask Web Application

server/
├── 🏗️ Application Core
│   ├── app.py                      Flask app factory
│   │   - Creates app with SQLAlchemy
│   │   - Registers blueprints
│   │   - Creates default admin
│   │   - Initializes SessionManager
│   │
│   └── wsgi.py                     WSGI entry point (NEW)
│       - For Render deployment
│       - Loads environment variables
│       - Runs gunicorn-compatible app
│
├── 🔐 Authentication & Routes
│   ├── auth.py                     Login/Logout/API auth (Updated)
│   │   - GET  /              Login page
│   │   - POST /login         Process login
│   │   - GET  /logout        Logout
│   │   - POST /api/auth      Bot client auth
│   │   - POST /api/verify_session  Session check
│   │
│   ├── admin.py                    Admin panel (Updated)
│   │   - GET  /admin/        Dashboard
│   │   - POST /admin/users/*  User management
│   │   - POST /admin/change_password  (With SessionManager cascade)
│   │   - POST /admin/ips/*   IP management
│   │   - POST /admin/notices/*  Notifications
│   │
│   └── user.py                     User dashboard (Updated)
│       - GET  /user/         Dashboard
│       - POST /user/devices/*/config  Update config
│       - POST /user/devices/*/bot/start  Start bot (Uses BotExecutor)
│       - POST /user/devices/*/bot/stop   Stop bot
│       - GET  /user/devices/*/bot/status  Get status
│       - GET  /user/api/config/*  Bot client config fetch
│       - POST /user/api/attack_count/*  Increment attacks
│
├── 🗄️ Database (NEW)
│   ├── models.py                   SQLAlchemy models (Updated)
│   │   - User              (admin/user roles, session_version)
│   │   - Device            (ADB devices per user)
│   │   - DeviceConfig      (Loot thresholds, attack limits)
│   │   - BotSession (NEW)  (Execution tracking)
│   │   - AuditLog (NEW)    (Action logging)
│   │   - BannedIP          (Access control)
│   │   - Notice            (Admin notifications)
│   │
│   └── coc_bot.db              Database file (Auto-created)
│
├── 🤖 Bot Execution (NEW)
│   ├── bot_executor.py            Bot process wrapper (NEW)
│   │   - BotExecutor class
│   │   - get_or_create() - Singleton per user/device
│   │   - start_bot() - Spawn process
│   │   - stop_bot() - Terminate process
│   │   - get_status() - Query status
│   │   - _monitor() - Watch subprocess
│   │
│   └── session_manager.py         Session management (NEW)
│       - SessionManager class
│       - initialize() - Load admin version on app start
│       - invalidate_all_sessions() - Cascade logout (admin password change)
│       - check_admin_password_changed() - Detect changes
│       - log_session_event() - Audit events
│
├── ⚙️ Configuration
│   ├── requirements.txt            Server dependencies (Updated)
│   │   - flask==3.0.0
│   │   - flask-sqlalchemy==3.1.1
│   │   - flask-socketio==5.3.6
│   │   - werkzeug==3.0.1
│   │   - gunicorn==21.2.0
│   │   - eventlet==0.33.3
│   │   - python-dotenv==1.0.0 (NEW)
│   │   - loguru==0.7.2 (NEW)
│   │
│   ├── Procfile                    Render start command (Updated)
│   │   - cd server && gunicorn --worker-class eventlet -w 1 'wsgi:app'
│   │
│   └── render.yaml                 Render manifest (Updated)
│       - Service config
│       - Build command
│       - Start command
│       - Environment variables
│
└── 🎨 Templates
    └── templates/
        ├── login.html              Login form
        ├── base.html               Base template
        ├── admin/
        │   └── dashboard.html      Admin dashboard
        └── user/
            └── dashboard.html      User dashboard

═══════════════════════════════════════════════════════════════

🔄 Data Flow

USER LOGIN
  1. GET /login (auth.py)
  2. POST /login with username/password
  3. Check credentials in User table
  4. Create session with session_version
  5. Redirect to /admin/ or /user/

ADMIN PASSWORD CHANGE
  1. POST /admin/change_password
  2. Hash new password, increment session_version
  3. Call SessionManager.invalidate_all_sessions()
  4. All User rows: session_version += 1
  5. All existing user sessions become invalid
  6. Next request: login_required redirects to /login

BOT START (User)
  1. POST /user/devices/<id>/bot/start
  2. Get DeviceConfig for device
  3. Create BotExecutor(user_id, device_id)
  4. call executor.start_bot(config_json)
  5. Create BotSession record
  6. Spawn bot_launcher.py as subprocess
  7. Return session_token to frontend
  8. _monitor() thread tracks process

BOT EXECUTION
  1. bot_launcher.py called by executor
  2. Receive device_id + config_json
  3. Parse config
  4. Initialize ADBController, Vision, CoCBot
  5. bot.run() - Farming loop
  6. Exit → BotSession marked as completed

═══════════════════════════════════════════════════════════════

📊 Database Schema

users
  - id (PK)
  - username (UNIQUE)
  - password_hash
  - role (admin/user)
  - is_banned
  - session_version (incremented on password change)
  - created_at

devices
  - id (PK)
  - user_id (FK → users)
  - device_name
  - adb_host
  - adb_port
  - is_active
  - created_at

device_configs
  - id (PK)
  - device_id (FK → devices, UNIQUE)
  - attack_limit
  - min_gold, min_elixir, min_dark
  - troops (JSON)
  - deploy_speed
  - bot_running
  - updated_at

bot_sessions
  - id (PK)
  - user_id (FK → users)
  - device_id (FK → devices)
  - session_token (UNIQUE)
  - started_at, ended_at
  - is_running
  - status (running/paused/stopped/error)
  - total_cycles, total_attacks, total_gold, etc.

audit_logs
  - id (PK)
  - user_id (FK → users)
  - action (login/logout/bot_start/bot_stop/etc)
  - resource (device_id, user_id, etc)
  - ip_address
  - timestamp
  - status (success/failure)

banned_ips
  - id (PK)
  - ip_address
  - user_id (FK → users, nullable)
  - reason
  - is_active
  - banned_at

notices
  - id (PK)
  - message
  - level (info/warning/danger)
  - is_active
  - created_by (FK → users)
  - created_at

═══════════════════════════════════════════════════════════════

✨ What's Different From Original Bot

BEFORE:
  - Desktop GUI only (customtkinter)
  - Local execution only
  - No multi-user support
  - No password management
  - No audit logging
  - Cannot deploy to cloud

AFTER:
  ✅ Web-based interface
  ✅ Multi-user support
  ✅ Admin controls
  ✅ Password management
  ✅ Audit logging
  ✅ Cloud-ready (Render)
  ✅ No changes to core bot logic
  ✅ All existing bot files unchanged

═══════════════════════════════════════════════════════════════

🚀 READY TO DEPLOY

1. Local Testing:
   python setup.py
   run.bat (or ./run.sh)
   http://localhost:5000

2. Render Deployment:
   git push
   Create Web Service on Render
   Auto-deploys with render.yaml

3. First Login:
   admin / admin123
   Change password immediately!

═══════════════════════════════════════════════════════════════
