# app/__init__.py

from flask import Flask

def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.config.from_object('config.Config')

    with app.app_context():
        from .routes import init_routes
        init_routes(app)

    return app