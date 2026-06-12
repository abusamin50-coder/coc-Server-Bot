"""User panel — bot control, per-device config."""

import json
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, User, Device, DeviceConfig, Notice
from auth import login_required

user_bp = Blueprint("user", __name__)


# ─────────────────────────── Dashboard ────────────────────────────────────────

@user_bp.route("/")
@login_required
def dashboard():
    user    = User.query.get(session["user_id"])
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()

    devices = []
    for dev in user.devices:
        cfg = dev.config
        if not cfg:
            cfg = DeviceConfig(device_id=dev.id)
            db.session.add(cfg)
            db.session.commit()
        devices.append({"device": dev, "config": cfg})

    return render_template("user/dashboard.html",
                           user=user,
                           devices=devices,
                           notices=notices)


# ─────────────────────────── Device config update ─────────────────────────────

@user_bp.route("/devices/<int:device_id>/config", methods=["POST"])
@login_required
def update_config(device_id):
    device = Device.query.get_or_404(device_id)

    # User শুধু নিজের device edit করতে পারবে
    if device.user_id != session["user_id"]:
        flash("এই device এর access নেই।", "danger")
        return redirect(url_for("user.dashboard"))

    cfg = device.config
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
    flash("Config সেভ হয়েছে।", "success")
    return redirect(url_for("user.dashboard"))


# ─────────────────────────── Bot start/stop ───────────────────────────────────

@user_bp.route("/devices/<int:device_id>/bot/start", methods=["POST"])
@login_required
def bot_start(device_id):
    device = Device.query.get_or_404(device_id)

    if device.user_id != session["user_id"]:
        return jsonify({"ok": False, "reason": "access_denied"}), 403

    cfg = device.config
    if cfg:
        cfg.bot_running = True
        db.session.commit()

    return jsonify({"ok": True, "status": "running"})


@user_bp.route("/devices/<int:device_id>/bot/stop", methods=["POST"])
@login_required
def bot_stop(device_id):
    device = Device.query.get_or_404(device_id)

    if device.user_id != session["user_id"]:
        return jsonify({"ok": False, "reason": "access_denied"}), 403

    cfg = device.config
    if cfg:
        cfg.bot_running = False
        db.session.commit()

    return jsonify({"ok": True, "status": "stopped"})


# ─────────────────────────── API — config fetch for .exe ──────────────────────

@user_bp.route("/api/config/<int:device_id>", methods=["GET"])
def api_get_config(device_id):
    """Bot .exe প্রতিটা start এ এখান থেকে latest config নেবে।"""
    user_id = request.args.get("user_id", type=int)
    sv      = request.args.get("sv", type=int)

    user = User.query.get(user_id)
    if not user or user.session_version != sv or user.is_banned:
        return jsonify({"ok": False, "reason": "unauthorized"}), 401

    device = Device.query.get_or_404(device_id)
    if device.user_id != user_id:
        return jsonify({"ok": False, "reason": "access_denied"}), 403

    cfg = device.config
    if not cfg:
        return jsonify({"ok": False, "reason": "no_config"}), 404

    return jsonify({
        "ok":           True,
        "attack_limit": cfg.attack_limit,
        "attacks_today":cfg.attacks_today,
        "min_gold":     cfg.min_gold,
        "min_elixir":   cfg.min_elixir,
        "min_dark":     cfg.min_dark,
        "troops":       json.loads(cfg.troops),
        "deploy_speed": cfg.deploy_speed,
        "delays":       json.loads(cfg.delays) if cfg.delays else {},
        "bot_running":  cfg.bot_running,
    })


@user_bp.route("/api/attack_count/<int:device_id>", methods=["POST"])
def api_increment_attack(device_id):
    """Bot .exe প্রতিটা attack শেষে call করবে।"""
    user_id = request.json.get("user_id")
    sv      = request.json.get("session_version")

    user = User.query.get(user_id)
    if not user or user.session_version != sv or user.is_banned:
        return jsonify({"ok": False}), 401

    device = Device.query.get_or_404(device_id)
    cfg    = device.config

    if cfg:
        from datetime import datetime, date
        # দিন পরিবর্তন হলে reset
        if cfg.last_reset and cfg.last_reset.date() < date.today():
            cfg.attacks_today = 0
            cfg.last_reset    = datetime.utcnow()

        cfg.attacks_today += 1
        db.session.commit()

        limit_reached = cfg.attacks_today >= cfg.attack_limit
        return jsonify({
            "ok":           True,
            "attacks_today":cfg.attacks_today,
            "attack_limit": cfg.attack_limit,
            "limit_reached":limit_reached,
        })

    return jsonify({"ok": False}), 404
