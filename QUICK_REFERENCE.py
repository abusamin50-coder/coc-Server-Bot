#!/usr/bin/env python3
"""Quick Reference — Commands & Endpoints"""

print("""
╔════════════════════════════════════════════════════════════════╗
║         CoC Bot Server — Quick Reference                       ║
╚════════════════════════════════════════════════════════════════╝

📋 LOCAL DEVELOPMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  Setup
   python setup.py

2️⃣  Activate venv
   venv\\Scripts\\activate    (Windows)
   source venv/bin/activate  (macOS/Linux)

3️⃣  Run server
   run.bat         (Windows)
   ./run.sh        (macOS/Linux)

4️⃣  Open browser
   http://localhost:5000

5️⃣  Test Login
   Username: admin
   Password: admin123

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 WEB ROUTES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

LOGIN & AUTH
  GET  /              → Login page
  GET  /login         → Login page (alias)
  POST /login         → Process login
  GET  /logout        → Logout

ADMIN PANEL
  GET  /admin/        → Dashboard
  POST /admin/users/add → Create user
  POST /admin/users/<id>/delete → Delete user
  POST /admin/users/<id>/ban → Ban user
  POST /admin/users/<id>/reset_password → Reset password
  POST /admin/change_password → Change admin password
  POST /admin/ips/ban → Ban IP
  POST /admin/ips/<id>/unban → Unban IP
  POST /admin/notices/add → Add notice
  POST /admin/notices/<id>/delete → Delete notice

USER PANEL
  GET  /user/ → Dashboard
  POST /user/devices/<id>/config → Update config
  POST /user/devices/<id>/bot/start → Start bot
  POST /user/devices/<id>/bot/stop → Stop bot
  GET  /user/devices/<id>/bot/status → Get status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔌 API ENDPOINTS (Bot Client)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AUTH
  POST /auth/api/auth           → Login
  POST /auth/api/verify_session → Check session

CONFIG
  GET  /user/api/config/<device_id>         → Fetch config
  POST /user/api/attack_count/<device_id>   → Increment attacks

BOT CONTROL
  POST /user/devices/<id>/bot/start  → Start execution
  POST /user/devices/<id>/bot/stop   → Stop execution
  GET  /user/devices/<id>/bot/status → Get status

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 DATABASE MODELS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User (users)
  - id, username, password_hash, role, is_banned, session_version

Device (devices)
  - id, user_id, device_name, adb_host, adb_port, is_active

DeviceConfig (device_configs)
  - id, device_id, attack_limit, min_gold, min_elixir, min_dark
  - troops (JSON), deploy_speed, bot_running

BotSession (bot_sessions)
  - id, user_id, device_id, session_token, started_at, ended_at
  - status, total_cycles, total_attacks, total_gold, etc.

AuditLog (audit_logs)
  - id, user_id, action, resource, ip_address, timestamp, status

BannedIP (banned_ips)
  - id, ip_address, user_id, reason, is_active

Notice (notices)
  - id, message, level, is_active, created_by

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 DEPLOYMENT (Vercel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  Git push
   git add -A && git commit -m "Deploy bot server" && git push

2️⃣  Vercel dashboard
   → Import Project
   → Connect GitHub repo
   → Select Python runtime
   → Set root to repository root

3️⃣  Auto-uses:
   ✅ vercel.json (deployment config)
   ✅ server/requirements.txt (dependencies)
   ✅ server/wsgi.py (entry point)

4️⃣  Set environment variables:
   SECRET_KEY=<your-secret-key>
   MONGODB_URI=<your-mongodb-uri>
   MONGODB_DB=<your-mongodb-database>
   FLASK_ENV=production

5️⃣  Deploy & visit
   https://your-app-name.vercel.app

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️  FILE LOCATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAIN FILES
  server/app.py              → Flask app factory
  server/wsgi.py             → Vercel entry point
  server/models.py           → MongoDB models
  server/auth.py             → Login/logout routes
  server/admin.py            → Admin dashboard
  server/user.py             → User dashboard
  server/bot_executor.py     → Bot process wrapper
  server/session_manager.py  → Session management

BOT FILES
  bot_launcher.py            → Bot process launcher
  bot_engine.py              → Farming logic (unchanged)
  adb_controller.py          → ADB control (unchanged)

CONFIG
  .env.example               → Environment template
  vercel.json               → Vercel deployment config

DOCS
  DEPLOYMENT.md              → Full deployment guide
  IMPLEMENTATION_COMPLETE.md → What was built
  README.md                  → Original bot documentation

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔒 SECURITY FEATURES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Password hashing (werkzeug)
✅ Session validation on every request
✅ Admin password change → all users logout
✅ User ban with session kill
✅ IP banning support
✅ Audit logging (all actions)
✅ CSRF protection
✅ HTTPOnly session cookies
✅ No file downloads allowed
✅ Permission-based access

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 TROUBLESHOOTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Bot won't start?
  → Check logs/bot_<device_id>.log
  → Verify ADB device_id in config
  → Test: adb connect <host>:<port>

Session expired?
  → Admin changed password
  → Browser closed
  → Login again

Permission denied?
  → Verify user role (admin/user)
  → Check IP ban status
  → Check if user is banned

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ READY TO DEPLOY! 🚀

Run locally: run.bat (Windows) or ./run.sh (Unix)
Deploy: Push to GitHub → Connect Vercel project
""")
