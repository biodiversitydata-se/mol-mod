#!/usr/bin/env python3

import json
import os
from functools import wraps

import logging
import requests
from logging.config import dictConfig
from flask import Flask, render_template, request
from flask_cas import CAS, login_required
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

from config import get_config
import errors

CONFIG = get_config()


def cas_server_available():
    url = CONFIG.CAS_SERVER
    # Simulate Service Unavailable
    # url = "https://httpbin.org/status/503"
    response = requests.get(url)
    if response.status_code == 200:
        return True
    else:
        logging.error(f"CAS server not working: {response.status_code}")
        return False


def custom_login_required(route_function):
    '''Adds CAS server status check to original Flask-CAS decorator, so that
       users are only sent to CAS login if server is working properly.
       Otherwise sends custom error message'''
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if cas_server_available():
            return login_required(route_function)(*args, **kwargs)
        else:
            hdr = 'Authentication problem'
            msg = '''
            Sorry, we can't forward you to login, because the SBDI
            authentication service is not working at the moment.'''
            return render_template('error_generic.html',
                                   name=hdr, description=msg,
                                   drop_contact=True)
    return wrapper


def create_app():
    """Application factory"""

    # Figure out environment to set log config
    environment = os.getenv('RUN_ENV')
    if environment != 'production':
        environment = 'development'

    # Load log config, and create log before flask app
    log_config = json.load(open(f'log/log_config_{environment}.json'))
    dictConfig(log_config)

    # Create flask app
    app = Flask(__name__)
    app.config.from_object(get_config())

    # Show e.g. Kungsängen correctly in JSON
    app.json.ensure_ascii = False

    # Add separate handler for werkzeug request/traffic info,
    # but set log level to same as for flask log
    werkzeug_log = logging.getLogger('werkzeug')
    werkzeug_log.setLevel(logging.root.level)

    # Note that if FLASK_DEBUG=1 (see compose file), Flask automatically sets
    # log-level to DEBUG. To override this with level set in log config:
    # app.logger.setLevel(logging.root.level)
    # To check actual level:
    # actual = logging.getLevelName(app.logger.getEffectiveLevel())
    # print(f"Logger's actual level: {actual}")

    # Enable cross-site resource forgery protections
    CSRFProtect(app)

    # Enable authentication against Bioatlas CAS server
    cas = CAS(app)

    # Enable flask email
    app.mail = Mail(app)

    # Make some variables available in all templates,
    # e.g. for dynamic display of menu items and email links
    @app.context_processor
    def inject_into_templates():
        if cas.attributes:
            user = cas.username
            # To show in menu when user is logged in
            firstname = cas.attributes['cas:firstname']
        else:
            user = None
            firstname = None
        # Pass global variables (used by multiple pages)
        # See forms.py for page-specific variables
        return dict(
            sbdi_contact_page=CONFIG.SBDI_CONTACT_PAGE,
            sbdi_start_page=CONFIG.SBDI_START_PAGE,
            taxonomy_page=CONFIG.TAXONOMY_PAGE,
            ena_guide_page=CONFIG.ENA_GUIDE_PAGE,
            ampliseq_page=CONFIG.AMPLISEQ_PAGE,
            ipt_base_url=CONFIG.IPT_BASE_URL,
            user=user,
            firstname=firstname,
            max_file_size=CONFIG.MAX_CONTENT_LENGTH,
            valid_extensions=', '.join(CONFIG.VALID_EXTENSIONS)
        )

    @app.before_request
    def flag_maintenance():
        '''Determines whether requested route is affected by maintenance,
           by checking two environment variables set using Makefile rules.'''
        if CONFIG.MAINTENANCE_MODE == 1:
            hdr = 'Site Maintenance'
            route_str = CONFIG.MAINTENANCE_ROUTES
            # If no routes have been specified, apply to all
            if route_str == 'All':
                msg = '''Sorry, the ASV portal is currently undergoing maintenance.
                         Please come back later.'''
                return render_template('error_generic.html',
                                       name=hdr, description=msg,
                                       drop_start=True)
            # Otherwise limit to specified routes,
            # e.g. when archives are being exported, or blast database is
            # being rebuilt
            else:
                routes = ['/' + r for r in route_str.split()]
                if request.path in routes:
                    msg = '''Sorry, this page is currently undergoing maintenance.
                             Please come back later.'''
                    return render_template('error_generic.html',
                                           name=hdr, description=msg)

    with app.app_context():
        from routes import blast_routes, filter_routes, main_routes
        app.register_blueprint(main_routes.main_bp)
        app.register_blueprint(blast_routes.blast_bp)
        app.register_blueprint(filter_routes.filter_bp)
        errors.init_app(app)

    return app
