import os
from flask import Flask
from .config import Config
try:
    from .database import init_db
except ImportError:
    init_db = None

def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=False,
        template_folder="templates",   # inside app/
        static_folder="static"         # inside app/
    )
    app.config.from_object(Config())

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config.get("UPLOAD_FOLDER", "storage"), exist_ok=True)

    with app.app_context():
        if init_db:
            try:
                init_db()
            except Exception as e:
                app.logger.error(f"Database init failed: {e}")

    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    @app.get("/health")
    def health():
        return "ok", 200

    return app
