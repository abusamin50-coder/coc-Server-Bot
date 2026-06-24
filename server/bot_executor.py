"""Bot Executor — web থেকে bot চালানোর জন্য."""

import os
import sys
import json
import secrets
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from models import db, BotSession, DeviceConfig, Device, AuditLog

# Parent directory add করি
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger


class BotExecutor:
    _instances = {}
    _lock = threading.Lock()

    def __init__(self, user_id: int, device_id: int):
        self.user_id = user_id
        self.device_id = device_id
        self.session_token = secrets.token_hex(32)
        self.process = None
        self.running = False
        self.stats = {"cycles": 0, "attacks": 0, "gold": 0, "elixir": 0, "dark": 0}

    @classmethod
    def get_or_create(cls, user_id: int, device_id: int):
        key = f"{user_id}_{device_id}"
        if key not in cls._instances:
            cls._instances[key] = cls(user_id, device_id)
        return cls._instances[key]

    def start_bot(self, config_path: str):
        """Bot process start করা"""
        if self.running:
            return {"error": "Bot already running"}

        try:
            session = BotSession(
                user_id=self.user_id,
                device_id=self.device_id,
                session_token=self.session_token,
                is_running=True,
                status="running"
            )
            db.session.add(session)
            db.session.commit()

            # Python bot launch
            bot_script = Path(__file__).parent.parent / "bot_launcher.py"
            self.process = subprocess.Popen(
                [sys.executable, str(bot_script), str(self.device_id), config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
            )
            
            self.running = True
            threading.Thread(target=self._monitor, daemon=True).start()

            return {
                "success": True,
                "session_token": self.session_token,
                "message": "Bot started"
            }
        except Exception as e:
            logger.error(f"Bot start error: {e}")
            return {"error": str(e)}

    def stop_bot(self):
        """Bot stop করা"""
        if not self.running or not self.process:
            return {"error": "Bot not running"}

        try:
            if os.name == 'nt':
                os.killpg(os.getpgid(self.process.pid), 15)
            else:
                self.process.terminate()
            
            self.process.wait(timeout=5)
            self.running = False

            session = BotSession.query.filter_by(session_token=self.session_token).first()
            if session:
                session.is_running = False
                session.ended_at = datetime.utcnow()
                session.status = "stopped"
                db.session.commit()

            return {"success": True, "message": "Bot stopped"}
        except Exception as e:
            logger.error(f"Bot stop error: {e}")
            return {"error": str(e)}

    def get_status(self):
        """Bot status জানা"""
        if not self.running:
            return {"status": "stopped"}

        session = BotSession.query.filter_by(session_token=self.session_token).first()
        if session:
            return {
                "status": session.status,
                "cycles": session.total_cycles,
                "attacks": session.total_attacks,
                "gold": session.total_gold,
                "elixir": session.total_elixir,
                "dark": session.total_dark,
                "running_time": str(datetime.utcnow() - session.started_at)
            }
        return {"status": "unknown"}

    def _monitor(self):
        """Process monitoring"""
        try:
            self.process.wait()
            self.running = False
            
            session = BotSession.query.filter_by(session_token=self.session_token).first()
            if session:
                session.is_running = False
                session.ended_at = datetime.utcnow()
                session.status = "completed"
                db.session.commit()
        except Exception as e:
            logger.error(f"Monitor error: {e}")


def log_audit(user_id: int, action: str, ip_address: str, resource: str = None, status: str = "success"):
    """Audit log করা"""
    try:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            status=status
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        logger.error(f"Audit log error: {e}")
