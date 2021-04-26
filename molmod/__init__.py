#!/usr/bin/env python3

import json
import logging
import os
from logging.config import dictConfig

from flask import Flask
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

    # Make some variables available in all templates
    @app.context_processor
    def inject_into_templates():
        CONFIG = get_config()
        logging.debug(CONFIG.SBDI_CONTACT_PAGE)

        return dict(
            sbdi_contact_page=CONFIG.SBDI_CONTACT_PAGE,
            sbdi_start_page=CONFIG.SBDI_START_PAGE,
            sbdi_seq_search_page=CONFIG.SBDI_SEQ_SEARCH_PAGE,
            sbdi_molecular_page=CONFIG.SBDI_MOLECULAR_PAGE,
            bioatlas_page=CONFIG.BIOATLAS_PAGE,
            taxonomy_page=CONFIG.TAXONOMY_PAGE
        )

    with app.app_context():
        from molmod.routes import blast_routes, filter_routes, main_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
