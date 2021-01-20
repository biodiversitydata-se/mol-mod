#!/usr/bin/env python3

import os
import json

from logging.config import dictConfig

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import get_config
from . import errors


def create_app():
    '''Application factory'''

    # Figure out environment to set log config
    environment = os.getenv('FLASK_ENV')
    if environment != 'production':
        environment == 'develop'

    # Load log config, and create the log before the flask app, so that the
    # flask app picks up the config when it's created.
    log_config = json.load(open(f'log/log_config_{environment}.json'))
    dictConfig(log_config)

    # Create flask app
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
