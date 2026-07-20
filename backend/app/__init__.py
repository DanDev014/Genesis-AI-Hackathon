from flask import Flask


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return {"message": "Genesis AI Backend is running"}

    return app