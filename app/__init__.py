import os
from flask import Flask

from .config import Config
from .database import init_db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config())

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        init_db()

    from .routes import bp as main_bp

    app.register_blueprint(main_bp)

    return app
