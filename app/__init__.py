import os
from flask import Flask
from .config import Config

# Try importing DB setup, but don’t crash if missing
try:
    from .database import init_db
except ImportError:
    init_db = None


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config())

    if test_config:
        app.config.update(test_config)

    # --- SAFETY: Ensure upload and data folders exist ---
    upload_dir = app.config.get("UPLOAD_FOLDER", "storage")
    os.makedirs(upload_dir, exist_ok=True)

    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)

    # --- SAFETY: Initialize database if possible ---
    with app.app_context():
        if init_db:
            try:
                init_db()
            except Exception as e:
                app.logger.error(f"Database init failed: {e}")

    # --- ROUTES ---
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # --- SIMPLE HEALTH ROUTE (for Render testing) ---
    @app.route("/health")
    def health():
        return "ok", 200

    return app
