# CoC Auto Farming Bot - Server Edition

Professional bot control panel for Clash of Clans farming with web-based authentication and management.

## ✨ Features

- 🔐 Web-based login system (username/password)
- 👥 Admin panel for user management
- 🤖 Bot control from web interface
- 📊 Real-time stats tracking
- 🔑 Admin-only password change (logs out all users)
- 🚫 No file download capability
- 📝 Complete audit logging
- 📱 Per-device configuration
- ⚙️ Loot threshold management

## 🚀 Quick Start (Local)

### 1. Setup Python Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
pip install -r server/requirements.txt
```

### 3. Run Server
```bash
cd server
python -c "from app import create_app; app = create_app(); from flask_socketio import SocketIO; SocketIO(app).run(app, host='0.0.0.0', port=5000)"
```

### 4. Default Credentials
- Username: `admin`
- Password: `admin123`
- ⚠️ Change immediately after first login!

### 5. Access
- Web: http://localhost:5000
- Login and manage devices

## 🌐 Vercel Deployment

### 1. Create New Project on Vercel
- Select "Import Project"
- Connect your GitHub repo
- Choose Python runtime

### 2. Build & Start Commands
Vercel will use `vercel.json` and `server/wsgi.py`.

### 3. Environment Variables
```
SECRET_KEY=<your-secret-key>
MONGODB_URI=<your-mongodb-uri>
MONGODB_DB=<your-mongodb-database>
FLASK_ENV=production
```

### 4. Deploy
Push to GitHub → Vercel auto-deploys

## 📁 Project Structure

```
.
├── adb_controller.py       (Android Debug Bridge)
├── bot_engine.py           (Farming logic)
├── bot_launcher.py         (Web → Bot launcher)
├── bot_client.py           (Desktop client - legacy)
├── gui.py                  (Desktop GUI - legacy)
├── config.yaml             (Bot configuration)
├── requirements.txt        (Root dependencies)
│
├── server/
│   ├── app.py              (Flask app)
│   ├── wsgi.py             (Vercel entry point)
│   ├── auth.py             (Login/auth routes)
│   ├── admin.py            (Admin panel)
│   ├── user.py             (User panel)
│   ├── models.py           (Database models)
│   ├── bot_executor.py     (Bot execution wrapper)
│   ├── session_manager.py  (Session tracking)
│   ├── requirements.txt    (Server dependencies)
│   ├── vercel.json         (Vercel config)
│   └── templates/
│       ├── login.html
│       ├── admin/dashboard.html
│       └── user/dashboard.html
│
└── logs/                   (Auto-generated)
```

## 🔐 Security Features

- ✅ Password hashing (werkzeug)
- ✅ Session validation on every request
- ✅ IP banning support
- ✅ User ban/unban
- ✅ Admin password change invalidates all sessions
- ✅ Audit logging for all actions
- ✅ No direct file access
- ✅ CSRF protection via Flask sessions

## 📝 User Management (Admin)

### Create User
Admin Dashboard → "Add User" → Username + Password

### Reset User Password
Admin Dashboard → User → "Reset Password"
- Invalidates user's current sessions
- User must login again

### Ban User
Admin Dashboard → User → "Ban"
- Immediate session termination
- Future login attempts blocked
- Can unban later

### Admin Password Change
Admin Dashboard → "Change Password"
- All regular users logout immediately
- Admin session continues
- Security event logged

## 🎮 User Operations

### Login
1. Go to your Vercel app URL
2. Enter username & password
3. Select device
4. Configure attack settings

### Start Bot
1. Dashboard → Select device
2. Click "Start Bot"
3. Monitor status in real-time

### Configure Device
- Attack limit (per day)
- Loot thresholds (gold/elixir/dark)
- Troop settings
- Deploy speed

## 📊 Audit Log

Every action is logged:
- User login/logout
- Bot start/stop
- Configuration changes
- Password resets
- Admin actions
- Failed access attempts

Access via database: `audit_logs` table

## 🛠️ Troubleshooting

### Bot won't start
- Check ADB connection in config
- Verify device IP and port
- Check server logs: `logs/bot_*.log`

### Session expired
- Password was changed by admin
- Session timeout (browser closed)
- Login again

### Can't login
- Verify username/password
- Check if account is banned
- Review audit logs

## 📞 Support

Check logs in:
- `logs/bot.log` - Server activity
- `logs/bot_<device_id>.log` - Bot execution
- Database: `audit_logs` table

## ⚠️ Important

1. **Change admin password immediately** after first deployment
2. Keep `SECRET_KEY` secret in production
3. Use HTTPS in production (Vercel provides SSL)
4. Backup database regularly
5. Monitor audit logs for suspicious activity
