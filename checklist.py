"""Pre-deployment checklist."""

import os
import sys
from pathlib import Path

def check(condition, message):
    status = "✅" if condition else "❌"
    print(f"{status} {message}")
    return condition

def main():
    print("📋 Pre-Deployment Checklist\n")
    
    all_good = True
    
    # Directory structure
    print("📁 Directory Structure:")
    all_good &= check(Path("server").exists(), "server/ exists")
    all_good &= check(Path("server/templates").exists(), "server/templates/ exists")
    all_good &= check(Path("logs").exists(), "logs/ exists")
    
    # Files
    print("\n📄 Required Files:")
    files = [
        "server/app.py",
        "server/auth.py",
        "server/admin.py",
        "server/user.py",
        "server/models.py",
        "server/bot_executor.py",
        "server/session_manager.py",
        "server/wsgi.py",
        "server/requirements.txt",
        "server/Procfile",
        "bot_launcher.py",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "DEPLOYMENT.md",
    ]
    for f in files:
        all_good &= check(Path(f).exists(), f"{f}")
    
    # Dependencies
    print("\n📦 Dependencies:")
    if Path("requirements.txt").exists():
        with open("requirements.txt") as f:
            content = f.read().lower()
            all_good &= check("opencv" in content, "opencv-python in requirements.txt")
            all_good &= check("loguru" in content, "loguru in requirements.txt")
    
    if Path("server/requirements.txt").exists():
        with open("server/requirements.txt") as f:
            content = f.read().lower()
            all_good &= check("flask" in content, "flask in server/requirements.txt")
            all_good &= check("sqlalchemy" in content, "sqlalchemy in server/requirements.txt")
            all_good &= check("python-dotenv" in content, "python-dotenv in server/requirements.txt")
    
    # Database models
    print("\n🗄️  Database Models:")
    if Path("server/models.py").exists():
        with open("server/models.py") as f:
            content = f.read()
            all_good &= check("class BotSession" in content, "BotSession model exists")
            all_good &= check("class AuditLog" in content, "AuditLog model exists")
            all_good &= check("class User" in content, "User model exists")
    
    # Bot executor
    print("\n🤖 Bot Executor:")
    all_good &= check(Path("server/bot_executor.py").exists(), "bot_executor.py exists")
    if Path("server/bot_executor.py").exists():
        with open("server/bot_executor.py") as f:
            content = f.read()
            all_good &= check("def start_bot" in content, "start_bot() method exists")
            all_good &= check("def stop_bot" in content, "stop_bot() method exists")
    
    # Session manager
    print("\n🔐 Session Manager:")
    all_good &= check(Path("server/session_manager.py").exists(), "session_manager.py exists")
    if Path("server/session_manager.py").exists():
        with open("server/session_manager.py") as f:
            content = f.read()
            all_good &= check("def invalidate_all_sessions" in content, "invalidate_all_sessions() exists")
    
    # Bot launcher
    print("\n🚀 Bot Launcher:")
    all_good &= check(Path("bot_launcher.py").exists(), "bot_launcher.py exists")
    if Path("bot_launcher.py").exists():
        with open("bot_launcher.py") as f:
            content = f.read()
            all_good &= check("from bot_engine import CoCBot" in content, "imports CoCBot")
    
    # Configuration
    print("\n⚙️  Configuration:")
    all_good &= check(Path(".env.example").exists(), ".env.example exists")
    all_good &= check(Path("server/render.yaml").exists(), "render.yaml exists")
    all_good &= check(Path("server/Procfile").exists(), "Procfile exists")
    
    # Security
    print("\n🔒 Security Checks:")
    if Path(".env.example").exists():
        with open(".env.example") as f:
            content = f.read()
            all_good &= check("change-this" in content.lower() or "change" in content.lower(), ".env.example has security warning")
    
    print("\n" + "="*50)
    if all_good:
        print("✅ All checks passed! Ready to deploy.")
    else:
        print("❌ Some checks failed. Please fix issues above.")
        sys.exit(1)
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
