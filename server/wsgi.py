"""WSGI entry point for production deployment (Render/Vercel)."""

import os
import sys
from pathlib import Path
import traceback

# Ensure .env is loaded FIRST, before any imports
from dotenv import load_dotenv
load_dotenv(verbose=True)

# Verify MongoDB URI is loaded
mongodb_uri = os.environ.get('MONGODB_URI')
if not mongodb_uri:
    print("ERROR: MONGODB_URI not set in environment", file=sys.stderr)
    sys.exit(1)

# Server directory add to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app import create_app
    print(f"✓ Successfully imported create_app", file=sys.stderr)
except Exception as e:
    print(f"ERROR: failed to import create_app from server.app: {e}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

try:
    app = create_app()
    print("✓ Flask app created successfully", file=sys.stderr)
except Exception as e:
    print(f"ERROR: create_app() raised exception: {e}", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
