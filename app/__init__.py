#!/usr/bin/env python

import os

from flask import Flask


def create_app():
    '''Application factory'''
    # Initialize core app (config path relative to app root)
    # 'app' variable = Flask instance
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(os.environ['APP_SETTINGS'])

    from app.main import main_routes
    app.register_blueprint(main_routes.main_bp)

    from app.admin import admin_routes
    app.register_blueprint(admin_routes.admin_bp)

    return app
