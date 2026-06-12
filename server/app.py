"""Main Flask application — CoC Bot Control Panel."""

import eventlet
eventlet.monkey_patch()

import os
from flask import Flask
from flask_socketio import SocketIO
from models import db
from auth import auth_bp
from admin import admin_bp
from user import user_bp

socketio = SocketIO()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"]           = os.environ.get("SECRET_KEY", "coc-bot-secret-change-in-prod")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///coc_bot.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="eventlet")

    # Jinja2 custom filter — template এ {{ value | fromjson }} কাজ করবে
    import json as _json
    app.jinja_env.filters["fromjson"] = _json.loads

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(user_bp,  url_prefix="/user")

    with app.app_context():
        db.create_all()
        _create_default_admin()

    return app


def _create_default_admin():
    """First run এ default admin তৈরি করা।"""
    from models import User
    from werkzeug.security import generate_password_hash

    if not User.query.filter_by(role="admin").first():
        admin = User(
            username      = "admin",
            password_hash = generate_password_hash("admin123"),
            role          = "admin",
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Default admin created — username: admin | password: admin123")
        print("⚠️  Please change the admin password immediately!")


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
