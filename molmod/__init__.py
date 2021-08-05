#!/usr/bin/env python3

import json
import logging
import os
from logging.config import dictConfig

from flask import Flask
from flask_cas import CAS
from flask_mail import Mail
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

    # Enable authentication against Bioatlas CAS server
    cas = CAS(app)

    # Enable flask email
    app.mail = Mail(app)

    # Make some variables available in all templates,
    # for dynamic display of menu items and email links
    @app.context_processor
    def inject_into_templates():
        CONFIG = get_config()
        if cas.attributes:
            user = cas.username
            # To show in menu when user is logged in
            firstname = cas.attributes['cas:firstname']
        else:
            user = None
            firstname = None

        return dict(
            sbdi_contact_page=CONFIG.SBDI_CONTACT_PAGE,
            sbdi_start_page=CONFIG.SBDI_START_PAGE,
            taxonomy_page=CONFIG.TAXONOMY_PAGE,
            ena_guide_page=CONFIG.ENA_GUIDE_PAGE,
            ampliseq_page=CONFIG.AMPLISEQ_PAGE,
            user=user,
            firstname=firstname,
            max_file_size=CONFIG.MAX_CONTENT_LENGTH,
            valid_extensions=', '.join(CONFIG.VALID_EXTENSIONS)
        )

    with app.app_context():
        from molmod.routes import blast_routes, filter_routes, main_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
