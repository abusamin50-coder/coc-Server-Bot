"""WSGI entry point for Vercel / production deployment."""

import os
import sys
from pathlib import Path
import traceback

# Server directory add
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

try:
    from app import create_app
except Exception:
    print("ERROR: failed to import create_app from server.app", file=sys.stderr)
    traceback.print_exc()
    raise

try:
    app = create_app()
except Exception:
    print("ERROR: create_app() raised an exception during app initialization", file=sys.stderr)
    traceback.print_exc()
    raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
