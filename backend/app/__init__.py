from flask import Flask

from app.config import Config
from app.extensions import db
import app.models 
from app.routes.test import test_bp

from .extensions import db, migrate, jwt, cors

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return {"message": "Genesis AI Backend is running"}

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)