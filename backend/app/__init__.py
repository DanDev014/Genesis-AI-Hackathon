from flask import Flask
from sqlalchemy import text
from .routes.auth import auth_bp

from .config import Config
from .extensions import db, migrate, jwt, cors




def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    @app.route("/")
    def index():
        return {"message": "Genesis AI Backend is running perfectly fine"}

    @app.route("/health/db")
    def database_health():
        db.session.execute(text("SELECT 1"))
        return {"database": "Connected successfully"}


    app.register_blueprint(auth_bp, url_prefix="/api")

    return app