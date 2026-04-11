import os

from dotenv import load_dotenv
from flask import Flask

from app.db import init_db

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    with app.app_context():
        init_db()

    # Auth
    from app.auth import auth_bp, login_manager, init_google_oauth
    login_manager.init_app(app)
    init_google_oauth(app)
    app.register_blueprint(auth_bp)

    # Main routes
    from app import routes
    app.register_blueprint(routes.bp)

    return app

