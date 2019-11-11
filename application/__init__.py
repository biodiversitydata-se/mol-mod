#!/usr/bin/env python

# Std lib
import os

# 3rd party
from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from flask_redis import FlaskRedis

# Globally accessible libraries
db = SQLAlchemy()
r = FlaskRedis()

def create_app():
    # Initialize core app (config path relative to app root)
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(os.environ['APP_SETTINGS'])

    # Initialize Plugins
    db.init_app(app)
    r.init_app(app)

    with app.app_context():

        from .main import main_routes
        from .admin import admin_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(admin_routes.admin_bp)

        # Create tables for our models
        db.create_all()

        return app
