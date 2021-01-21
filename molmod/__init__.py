#!/usr/bin/env python3

import os
import json
import logging

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
        environment = 'develop'

    # Load log config, and create the log before the flask app, so that the
    # flask app picks up the config when it's created.
    log_config = json.load(open(f'log/log_config_{environment}.json'))
    dictConfig(log_config)

    # Create flask app
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(get_config())

    # Request information is written to the werkzeug log, so we make sure that
    # this log is set to the same level as the flask log. In case traffic should
    # be logged to a different log than the rest of the app - add a separate
    # handler to this log.
    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.root.level)

    # Note that if the environment is set to 'develop', then the config module
    # will set FLASK_DEBUG=1, which will also set the log-level to DEBUG. if you
    # wish to override this, you can change the log level explicitly here, as:
    # app.logger.setLevel(logging.root.level)

    # enable cross-site resource forgery protections
    CSRFProtect(app)

    with app.app_context():
        from molmod.routes import main_routes, filter_routes, blast_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
