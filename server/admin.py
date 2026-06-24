"""Admin panel — user management, ban/unban, notices, password reset."""

import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash
from models import db, User, Device, DeviceConfig, BannedIP, Notice, AuditLog
from auth import admin_required, get_client_ip
from session_manager import SessionManager

admin_bp = Blueprint("admin", __name__)


# ─────────────────────────── Dashboard ────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    users      = User.query.filter_by(role="user").order_by(User.created_at.desc()).all()
    notices    = Notice.query.order_by(Notice.created_at.desc()).all()
    banned_ips = BannedIP.query.filter_by(is_active=True).all()
    total_devices = Device.query.count()
    active_bots   = DeviceConfig.query.filter_by(bot_running=True).count()

    return render_template("admin/dashboard.html",
                           users=users,
                           notices=notices,
                           banned_ips=banned_ips,
                           total_devices=total_devices,
                           active_bots=active_bots)


# ─────────────────────────── User Management ──────────────────────────────────

@admin_bp.route("/users/add", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Username এবং Password দিতে হবে।", "danger")
        return redirect(url_for("admin.dashboard"))

    if User.query.filter_by(username=username).first():
        flash(f"'{username}' নামে user আগে থেকেই আছে।", "danger")
        return redirect(url_for("admin.dashboard"))

    user = User(
        username      = username,
        password_hash = generate_password_hash(password),
        role          = "user",
    )
    db.session.add(user)
    db.session.commit()

    # Default device তৈরি করা
    device = Device(user_id=user.id, device_name=f"{username}'s Device")
    db.session.add(device)
    db.session.flush()

    cfg = DeviceConfig(device_id=device.id)
    db.session.add(cfg)
    db.session.commit()

    flash(f"User '{username}' তৈরি হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        flash("Admin delete করা যাবে না।", "danger")
        return redirect(url_for("admin.dashboard"))

    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' delete হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/reset_password", methods=["POST"])
@admin_required
def reset_password(user_id):
    user     = User.query.get_or_404(user_id)
    password = request.form.get("new_password", "").strip()

    if not password:
        flash("নতুন password দিতে হবে।", "danger")
        return redirect(url_for("admin.dashboard"))

    user.password_hash   = generate_password_hash(password)
    user.session_version += 1  # সব পুরনো session invalid করা
    db.session.commit()

    flash(f"'{user.username}' এর password reset হয়েছে। সব session logout হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    user   = User.query.get_or_404(user_id)
    reason = request.form.get("reason", "").strip()

    if user.role == "admin":
        flash("Admin কে ban করা যাবে না।", "danger")
        return redirect(url_for("admin.dashboard"))

    user.is_banned        = True
    user.ban_reason       = reason or "Admin কর্তৃক ban"
    user.banned_at        = datetime.utcnow()
    user.session_version += 1  # active session kill

    # সেই user এর সব device এর IP ban করা
    for device in user.devices:
        if device.adb_host and device.adb_host != "127.0.0.1":
            existing = BannedIP.query.filter_by(ip_address=device.adb_host, is_active=True).first()
            if not existing:
                db.session.add(BannedIP(
                    ip_address = device.adb_host,
                    user_id    = user_id,
                    reason     = reason or "User ban এর কারণে",
                ))

    db.session.commit()
    flash(f"'{user.username}' ban করা হয়েছে এবং session kill হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@admin_required
def unban_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_banned  = False
    user.ban_reason = None
    user.banned_at  = None

    # সেই user এর IP unban
    BannedIP.query.filter_by(user_id=user_id).update({"is_active": False})
    db.session.commit()

    flash(f"'{user.username}' unban করা হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


# ─────────────────────────── IP Management ────────────────────────────────────

@admin_bp.route("/ips/ban", methods=["POST"])
@admin_required
def ban_ip():
    ip     = request.form.get("ip_address", "").strip()
    reason = request.form.get("reason", "").strip()

    if not ip:
        flash("IP address দিতে হবে।", "danger")
        return redirect(url_for("admin.dashboard"))

    existing = BannedIP.query.filter_by(ip_address=ip, is_active=True).first()
    if existing:
        flash(f"IP {ip} আগে থেকেই banned।", "warning")
        return redirect(url_for("admin.dashboard"))

    db.session.add(BannedIP(ip_address=ip, reason=reason or "Manual ban"))
    db.session.commit()
    flash(f"IP {ip} ban করা হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/ips/<int:ban_id>/unban", methods=["POST"])
@admin_required
def unban_ip(ban_id):
    ban = BannedIP.query.get_or_404(ban_id)
    ban.is_active = False
    db.session.commit()
    flash(f"IP {ban.ip_address} unban হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


# ─────────────────────────── Notices ──────────────────────────────────────────

@admin_bp.route("/notices/add", methods=["POST"])
@admin_required
def add_notice():
    message = request.form.get("message", "").strip()
    level   = request.form.get("level", "info")

    if not message:
        flash("Notice message দিতে হবে।", "danger")
        return redirect(url_for("admin.dashboard"))

    db.session.add(Notice(
        message    = message,
        level      = level,
        created_by = session["user_id"],
    ))
    db.session.commit()
    flash("Notice যোগ হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/notices/<int:notice_id>/delete", methods=["POST"])
@admin_required
def delete_notice(notice_id):
    notice = Notice.query.get_or_404(notice_id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice delete হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/notices/<int:notice_id>/toggle", methods=["POST"])
@admin_required
def toggle_notice(notice_id):
    notice           = Notice.query.get_or_404(notice_id)
    notice.is_active = not notice.is_active
    db.session.commit()
    state = "চালু" if notice.is_active else "বন্ধ"
    flash(f"Notice {state} করা হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


# ─────────────────────────── Admin password change ────────────────────────────

@admin_bp.route("/change_password", methods=["POST"])
@admin_required
def change_password():
    new_password = request.form.get("new_password", "").strip()
    confirm      = request.form.get("confirm_password", "").strip()

    if not new_password or new_password != confirm:
        flash("Password মিলছে না বা খালি।", "danger")
        return redirect(url_for("admin.dashboard"))

    admin = User.query.get(session["user_id"])
    admin.password_hash   = generate_password_hash(new_password)
    admin.session_version += 1
    db.session.commit()

    # সব user দের session invalidate করা
    SessionManager.invalidate_all_sessions()

    # নিজের session update
    session["session_version"] = admin.session_version
    flash("Admin password পরিবর্তন হয়েছে। সব user logout হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))


# ─────────────────────────── Device config (admin view) ───────────────────────

@admin_bp.route("/devices/<int:device_id>/config", methods=["POST"])
@admin_required
def update_device_config(device_id):
    device = Device.query.get_or_404(device_id)
    cfg    = device.config

    if not cfg:
        cfg = DeviceConfig(device_id=device_id)
        db.session.add(cfg)

    cfg.attack_limit = int(request.form.get("attack_limit", cfg.attack_limit))
    cfg.min_gold     = int(request.form.get("min_gold",     cfg.min_gold))
    cfg.min_elixir   = int(request.form.get("min_elixir",   cfg.min_elixir))
    cfg.min_dark     = int(request.form.get("min_dark",     cfg.min_dark))
    cfg.deploy_speed = float(request.form.get("deploy_speed", cfg.deploy_speed))

    troops = request.form.getlist("troops")
    cfg.troops = json.dumps(troops)

    db.session.commit()
    flash("Device config আপডেট হয়েছে।", "success")
    return redirect(url_for("admin.dashboard"))
