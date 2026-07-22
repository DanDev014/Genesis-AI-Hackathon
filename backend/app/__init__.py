from flask import Flask
from sqlalchemy import text
from .routes.auth import auth_bp
from .routes.clients import clients_bp
from .routes.call_records import call_records_bp

from .routes.proposals import proposals_bp
from .routes.quotes import quotes_bp
from .routes.reports import reports_bp
from .routes.team_members import team_members_bp
from .routes.transcripts import transcripts_bp

from .config import Config
from .extensions import db, migrate, jwt, cors

from .routes.summaries import summaries_bp

from app.exceptions import AppError
from app.utils.responses import error_response




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

    @app.errorhandler(AppError)
    def handle_app_error(error):
        return error_response(
        error.message,
        error.status_code,
    )


    app.register_blueprint(auth_bp, url_prefix="/api")
    app.register_blueprint(clients_bp, url_prefix="/api")
    app.register_blueprint(call_records_bp, url_prefix="/api")
    app.register_blueprint(proposals_bp, url_prefix="/api")
    app.register_blueprint(quotes_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
    app.register_blueprint(team_members_bp, url_prefix="/api")
    app.register_blueprint(transcripts_bp, url_prefix="/api")
    app.register_blueprint(summaries_bp,url_prefix="/api")

    return app