#!/usr/bin/env python

import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect


def create_app():
    '''Application factory'''
    # Initialize core app (config path relative to app root)
    # 'app' variable = Flask instance
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(os.environ['APP_SETTINGS'])
    CSRFProtect(app)

    from app.main import main_routes
    app.register_blueprint(main_routes.main_bp)

    return app
