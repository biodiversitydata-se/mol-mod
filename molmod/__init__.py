#!/usr/bin/env python

import os

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from config import get_config


def create_app():
    '''Application factory'''
    # Initialize core app (config path relative to app root)
    # 'app' variable = Flask instance
    app = Flask(__name__, instance_relative_config=False)
    # app.config.from_object(get_env_variable('APP_SETTINGS'))
    app.config.from_object(get_config())
    CSRFProtect(app)

    with app.app_context():
        from molmod.main import main_routes
        app.register_blueprint(main_routes.main_bp)

    return app
