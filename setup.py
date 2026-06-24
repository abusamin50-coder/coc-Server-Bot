#!/usr/bin/env python3
"""Local development setup script."""

import os
import sys
import subprocess
from pathlib import Path

def run_cmd(cmd, description):
    print(f"\n📦 {description}...")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        sys.exit(1)
    print(f"✅ {description}")

def main():
    print("🚀 CoC Bot Server Setup\n")
    
    # Check Python version
    if sys.version_info < (3, 9):
        print("❌ Python 3.9+ required")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]}")
    
    # Create venv
    if not Path("venv").exists():
        run_cmd("python -m venv venv", "Creating virtual environment")
    
    # Activate venv
    venv_python = "venv/Scripts/python.exe" if os.name == 'nt' else "venv/bin/python"
    venv_pip = "venv/Scripts/pip.exe" if os.name == 'nt' else "venv/bin/pip"
    
    # Install dependencies
    run_cmd(f"{venv_pip} install --upgrade pip", "Upgrading pip")
    run_cmd(f"{venv_pip} install -r requirements.txt", "Installing root dependencies")
    run_cmd(f"{venv_pip} install -r server/requirements.txt", "Installing server dependencies")
    
    # Create .env
    if not Path(".env").exists():
        with open(".env", "w") as f:
            f.write("""SECRET_KEY=dev-secret-key-change-in-prod
FLASK_ENV=development
DATABASE_URL=sqlite:///coc_bot.db
""")
        print("✅ Created .env file")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    print("✅ Created logs directory")
    
    print("\n" + "="*50)
    print("✨ Setup complete!")
    print("="*50)
    print("\n📝 Next steps:")
    print("\n1. Activate virtual environment:")
    if os.name == 'nt':
        print("   venv\\Scripts\\activate")
    else:
        print("   source venv/bin/activate")
    
    print("\n2. Start server:")
    print("   cd server")
    print(f"   {venv_python} -c \"from app import create_app; app = create_app(); print('🚀 Server running at http://localhost:5000'); app.run(host='0.0.0.0', port=5000, debug=True)\"")
    
    print("\n3. Open browser:")
    print("   http://localhost:5000")
    
    print("\n4. Login with:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n⚠️  Change password immediately!\n")

if __name__ == "__main__":
    main()
