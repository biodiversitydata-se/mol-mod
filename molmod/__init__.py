#!/usr/bin/env python3
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import get_config
from . import errors


def create_app():
    '''Application factory'''
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config())
    CSRFProtect(app)

    with app.app_context():
        from molmod.routes import main_routes, filter_routes, blast_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
