"""Database models — SQLite via SQLAlchemy."""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(10), nullable=False, default="user")  # admin / user
    is_banned     = db.Column(db.Boolean, default=False)
    ban_reason    = db.Column(db.String(256), nullable=True)
    banned_at     = db.Column(db.DateTime, nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    # session_version বাড়লে সব পুরনো session invalid হবে
    session_version = db.Column(db.Integer, default=0)

    devices = db.relationship("Device", backref="owner", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class Device(db.Model):
    __tablename__ = "devices"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    device_name = db.Column(db.String(100), default="My Device")
    adb_host    = db.Column(db.String(50), default="127.0.0.1")
    adb_port    = db.Column(db.Integer, default=5555)
    is_active   = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    config = db.relationship("DeviceConfig", backref="device", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Device {self.device_name} ({self.adb_host}:{self.adb_port})>"


class DeviceConfig(db.Model):
    __tablename__ = "device_configs"

    id            = db.Column(db.Integer, primary_key=True)
    device_id     = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)

    # Attack settings
    attack_limit  = db.Column(db.Integer, default=50)        # per day
    attacks_today = db.Column(db.Integer, default=0)
    last_reset    = db.Column(db.DateTime, default=datetime.utcnow)

    # Loot thresholds
    min_gold      = db.Column(db.Integer, default=0)
    min_elixir    = db.Column(db.Integer, default=6000)
    min_dark      = db.Column(db.Integer, default=0)

    # Troop config (JSON string)
    troops        = db.Column(db.Text, default="[]")          # e.g. ["bb","art","gb"]
    deploy_speed  = db.Column(db.Float, default=0.08)

    # Delays (JSON string)
    delays        = db.Column(db.Text, default="{}")

    # Bot state
    bot_running   = db.Column(db.Boolean, default=False)

    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<DeviceConfig device_id={self.device_id}>"


class BannedIP(db.Model):
    __tablename__ = "banned_ips"

    id          = db.Column(db.Integer, primary_key=True)
    ip_address  = db.Column(db.String(45), nullable=False)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    reason      = db.Column(db.String(256), nullable=True)
    banned_at   = db.Column(db.DateTime, default=datetime.utcnow)
    is_active   = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<BannedIP {self.ip_address}>"


class Notice(db.Model):
    __tablename__ = "notices"

    id         = db.Column(db.Integer, primary_key=True)
    message    = db.Column(db.String(500), nullable=False)
    level      = db.Column(db.String(10), default="info")   # info / warning / danger
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    def __repr__(self):
        return f"<Notice {self.level}: {self.message[:40]}>"


class BotSession(db.Model):
    __tablename__ = "bot_sessions"

    id              = db.Column(db.Integer, primary_key=True)
    user_id         = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    device_id       = db.Column(db.Integer, db.ForeignKey("devices.id"), nullable=False)
    session_token   = db.Column(db.String(256), unique=True, nullable=False)
    
    started_at      = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at        = db.Column(db.DateTime, nullable=True)
    is_running      = db.Column(db.Boolean, default=True)
    
    total_cycles    = db.Column(db.Integer, default=0)
    total_attacks   = db.Column(db.Integer, default=0)
    total_gold      = db.Column(db.Integer, default=0)
    total_elixir    = db.Column(db.Integer, default=0)
    total_dark      = db.Column(db.Integer, default=0)
    
    status          = db.Column(db.String(50), default="running")  # running / paused / stopped / error
    error_message   = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"<BotSession {self.user_id}/{self.device_id}>"


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    action      = db.Column(db.String(100), nullable=False)
    resource    = db.Column(db.String(100), nullable=True)
    details     = db.Column(db.Text, nullable=True)
    ip_address  = db.Column(db.String(45), nullable=False)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    status      = db.Column(db.String(20), default="success")  # success / failure

    def __repr__(self):
        return f"<AuditLog {self.user_id}: {self.action}>"
