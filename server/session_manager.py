"""Session Manager — admin password change detect করে সবাইকে logout করাবে।"""

from datetime import datetime
from models import db, User, AuditLog


class SessionManager:
    _admin_version = None

    @classmethod
    def initialize(cls):
        """App start এ admin session version read করা"""
        admin = User.query.filter_by(role="admin").first()
        if admin:
            cls._admin_version = admin.session_version

    @classmethod
    def invalidate_all_sessions(cls):
        """সব user দের session invalid করা (admin password change পর)"""
        users = User.query.filter_by(role="user").all()
        for user in users:
            user.session_version += 1
        db.session.commit()

    @classmethod
    def check_admin_password_changed(cls):
        """Admin password change detect করা"""
        admin = User.query.filter_by(role="admin").first()
        if admin and admin.session_version != cls._admin_version:
            cls._admin_version = admin.session_version
            return True
        return False

    @classmethod
    def log_session_event(cls, user_id: int, event: str, ip_address: str):
        """Session event log করা"""
        try:
            audit = AuditLog(
                user_id=user_id,
                action="session_event",
                resource=event,
                ip_address=ip_address
            )
            db.session.add(audit)
            db.session.commit()
        except Exception:
            pass
