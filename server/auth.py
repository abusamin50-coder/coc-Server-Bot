"""Authentication — login, logout, session management."""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from models import db, User, BannedIP, Notice

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────── Helpers ──────────────────────────────────────────

def get_client_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr


def is_ip_banned(ip: str) -> bool:
    return BannedIP.query.filter_by(ip_address=ip, is_active=True).first() is not None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))

        user = User.query.get(session["user_id"])
        if not user or user.is_banned:
            session.clear()
            flash("তোমার account ban করা হয়েছে। Admin এর সাথে যোগাযোগ করো।", "danger")
            return redirect(url_for("auth.login"))

        # session_version check — password change হলে পুরনো session invalid
        if session.get("session_version") != user.session_version:
            session.clear()
            flash("Password পরিবর্তন হয়েছে। আবার login করো।", "warning")
            return redirect(url_for("auth.login"))

        # IP ban check
        if is_ip_banned(get_client_ip()):
            session.clear()
            flash("এই device থেকে access নেই। Admin এর সাথে যোগাযোগ করো।", "danger")
            return redirect(url_for("auth.login"))

        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("Admin access প্রয়োজন।", "danger")
            return redirect(url_for("auth.login"))
        return login_required(f)(*args, **kwargs)
    return decorated


# ─────────────────────────── Routes ───────────────────────────────────────────

@auth_bp.route("/", methods=["GET", "POST"])
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("user.dashboard"))

    notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        ip       = get_client_ip()

        # IP ban check
        if is_ip_banned(ip):
            error = "এই device থেকে access নেই। Admin এর সাথে যোগাযোগ করো।"
            return render_template("login.html", error=error, notices=notices)

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password_hash, password):
            error = "Username বা Password ভুল।"
        elif user.is_banned:
            reason = user.ban_reason or "কারণ জানানো হয়নি"
            error  = f"তোমার account ban করা হয়েছে। কারণ: {reason}। Admin এর সাথে যোগাযোগ করো।"
        else:
            session.clear()
            session["user_id"]         = user.id
            session["username"]        = user.username
            session["role"]            = user.role
            session["session_version"] = user.session_version
            session.permanent          = False  # browser বন্ধ করলে session শেষ

            if user.role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("user.dashboard"))

    return render_template("login.html", error=error, notices=notices)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logout সফল হয়েছে।", "info")
    return redirect(url_for("auth.login"))


# ─────────────────────────── API — Bot client auth ────────────────────────────

@auth_bp.route("/api/auth", methods=["POST"])
def api_auth():
    """Bot .exe এর জন্য — JSON login, config return করে।"""
    from flask import jsonify
    import json

    data     = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip       = get_client_ip()

    if is_ip_banned(ip):
        return jsonify({"ok": False, "reason": "ip_banned"}), 403

    user = User.query.filter_by(username=username).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"ok": False, "reason": "invalid_credentials"}), 401

    if user.is_banned:
        return jsonify({"ok": False, "reason": "banned", "message": user.ban_reason or ""}), 403

    # Return device configs for this user
    devices = []
    for dev in user.devices:
        cfg = dev.config
        devices.append({
            "device_id":    dev.id,
            "device_name":  dev.device_name,
            "adb_host":     dev.adb_host,
            "adb_port":     dev.adb_port,
            "attack_limit": cfg.attack_limit if cfg else 50,
            "attacks_today":cfg.attacks_today if cfg else 0,
            "min_gold":     cfg.min_gold if cfg else 0,
            "min_elixir":   cfg.min_elixir if cfg else 6000,
            "min_dark":     cfg.min_dark if cfg else 0,
            "troops":       json.loads(cfg.troops) if cfg else [],
            "deploy_speed": cfg.deploy_speed if cfg else 0.08,
            "delays":       json.loads(cfg.delays) if cfg else {},
        })

    notices = [
        {"message": n.message, "level": n.level}
        for n in Notice.query.filter_by(is_active=True).all()
    ]

    return jsonify({
        "ok":              True,
        "user_id":         user.id,
        "username":        user.username,
        "role":            user.role,
        "session_version": user.session_version,
        "devices":         devices,
        "notices":         notices,
    })


@auth_bp.route("/api/verify_session", methods=["POST"])
def api_verify_session():
    """Bot .exe প্রতিটা action এর আগে এটা call করবে।"""
    from flask import jsonify

    data     = request.get_json(silent=True) or {}
    user_id  = data.get("user_id")
    sv       = data.get("session_version")
    ip       = get_client_ip()

    if is_ip_banned(ip):
        return jsonify({"ok": False, "reason": "ip_banned"}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({"ok": False, "reason": "not_found"}), 404
    if user.is_banned:
        return jsonify({"ok": False, "reason": "banned"}), 403
    if user.session_version != sv:
        return jsonify({"ok": False, "reason": "session_expired"}), 401

    return jsonify({"ok": True})
