@echo off
REM Local development server runner for Windows

REM Activate venv
call venv\Scripts\activate.bat

REM Set environment
set FLASK_ENV=development
set FLASK_DEBUG=1

REM Run server
cd server
python -c "from app import create_app; from flask_socketio import SocketIO; app = create_app(); socketio = SocketIO(app); print('🚀 Server running at http://localhost:5000\n📝 Login: admin / admin123\n⚠️  Press Ctrl+C to stop\n'); socketio.run(app, host='0.0.0.0', port=5000, debug=True)"
