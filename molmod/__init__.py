#!/usr/bin/env python3

import json
import logging
import os
from logging.config import dictConfig

from flask import Flask
from flask_cas import CAS
from flask_wtf.csrf import CSRFProtect

from . import errors
from .config import get_config


def create_app():
    '''Application factory'''

    # Figure out environment to set log config
    environment = os.getenv('FLASK_ENV')
    if environment != 'production':
        environment = 'development'

    # Load log config, and create log before flask app
    log_config = json.load(open(f'log/log_config_{environment}.json'))
    dictConfig(log_config)

    # Create flask app
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Add separate handler for werkzeug request/traffic info,
    # but set log level to same as for flask log
    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.root.level)

    # Note that if environment is set to 'development', then the config module
    # will set FLASK_DEBUG=1, which will also set log-level to DEBUG.
    # To override this, change log level explicitly here:
    # app.logger.setLevel(logging.root.level)

    # Enable cross-site resource forgery protections
    CSRFProtect(app)

    cas = CAS(app)

    @app.context_processor
    def inject_user():
        return dict(user=cas.username)

    with app.app_context():
        from molmod.routes import blast_routes, filter_routes, main_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
