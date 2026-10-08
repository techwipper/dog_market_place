from pathlib import Path

from flask import Flask, render_template
from flask_login import current_user

from config import Config
from .extensions import db, login_manager


def create_app(config_class=Config):
    root = Path(__file__).resolve().parent.parent

    app = Flask(
        __name__,
        template_folder=str(root / "templates"),
        static_folder=str(root / "static"),
    )
    app.config.from_object(config_class)

    # --- folders ---
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["PROFILE_UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # --- extensions ---
    db.init_app(app)
    login_manager.init_app(app)

    # --- blueprints ---
    from .auth import auth_bp
    from .views import main_bp
    from .seller import seller_bp
    from .admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(seller_bp, url_prefix="/seller")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # --- template helpers ---
    @app.template_filter("money")
    def money(value):
        try:
            return f"{app.config['CURRENCY']}{float(value):,.0f}"
        except (TypeError, ValueError):
            return f"{app.config['CURRENCY']}0"

    @app.template_filter("since")
    def since(dt):
        if not dt:
            return ""
        delta = __import__("datetime").datetime.utcnow() - dt
        d = delta.days
        if d <= 0:
            hours = max(delta.seconds // 3600, 0)
            return f"{hours}h ago" if hours else "Just now"
        if d < 30:
            return f"{d}d ago"
        if d < 365:
            return f"{d // 30}mo ago"
        return f"{d // 365}y ago"

    @app.context_processor
    def inject_globals():
        return {
            "SITE_NAME": app.config["SITE_NAME"],
            "CURRENCY": app.config["CURRENCY"],
            "CONTACT_EMAIL": app.config["CONTACT_EMAIL"],
            "PAYMENT_MODE": app.config["PAYMENT_MODE"],
            "current_user": current_user,
        }

    # --- error pages ---
    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You don't have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="We couldn't find that page."), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("error.html", code=413,
                               message="That file is too large (8 MB maximum)."), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        return render_template("error.html", code=500,
                               message="Something went wrong on our side."), 500

    return app
