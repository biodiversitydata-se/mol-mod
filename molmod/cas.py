"""
Minimal CAS 2.0 client for Flask.

Based on Flask-CAS 1.0.2 (https://github.com/cameronbwhite/Flask-CAS, BSD
licence), which is unmaintained and incompatible with Flask >= 3.0. Only the
parts used by this app are kept: login/logout routes, service ticket
validation, the CAS object (username/attributes) and login_required.

Configuration (app.config):
    CAS_SERVER        Base URL of the CAS server (required)
    CAS_AFTER_LOGIN   Endpoint to redirect to after login from a page that
                      does not require login (required)
    CAS_AFTER_LOGOUT  URL that CAS redirects to after logout (optional)
"""

from functools import wraps
from urllib.parse import quote, urlencode, urljoin, urlsplit
from xml.parsers.expat import ExpatError

import requests
import xmltodict
from flask import Blueprint, current_app, redirect, request, session, url_for

TOKEN_KEY = '_CAS_TOKEN'
USERNAME_KEY = 'CAS_USERNAME'
ATTRIBUTES_KEY = 'CAS_ATTRIBUTES'
AFTER_LOGIN_KEY = 'CAS_AFTER_LOGIN_SESSION_URL'

LOGIN_ROUTE = '/cas'
LOGOUT_ROUTE = '/cas/logout'
VALIDATE_ROUTE = '/cas/serviceValidate'

blueprint = Blueprint('cas', __name__)


def _cas_url(route: str, **query) -> str:
    """Builds a URL on the CAS server, skipping query values that are None."""
    url = urljoin(current_app.config['CAS_SERVER'], quote(route))
    params = [(k, v) for k, v in query.items() if v is not None]
    return f'{url}?{urlencode(params)}' if params else url


def _service_url() -> str:
    """The URL that CAS sends the user back to (with a ticket) after login."""
    return url_for('cas.login', origin=session.get(AFTER_LOGIN_KEY),
                   _external=True)


def _is_local_path(url: str) -> bool:
    """True for site-relative paths, to avoid redirecting to other hosts."""
    parts = urlsplit(url)
    return (not parts.scheme and not parts.netloc
            and url.startswith('/') and not url.startswith('//'))


def _validate(ticket: str) -> bool:
    """
    Validates a service ticket against CAS. On success, stores username and
    attributes in the session and returns True.
    """
    validate_url = _cas_url(VALIDATE_ROUTE, service=_service_url(),
                            ticket=ticket)
    try:
        response = requests.get(validate_url, timeout=10)
        response.raise_for_status()
        result = xmltodict.parse(response.text)['cas:serviceResponse']
    except (requests.RequestException, KeyError, ValueError,
            ExpatError) as e:
        current_app.logger.error(f'CAS ticket validation failed: {e}')
        return False

    success = result.get('cas:authenticationSuccess')
    if not success:
        current_app.logger.debug('CAS ticket invalid')
        return False

    session[USERNAME_KEY] = success['cas:user']
    if 'cas:attributes' in success:
        session[ATTRIBUTES_KEY] = success['cas:attributes']
    return True


@blueprint.route('/login/')
def login():
    """
    Sends the user to CAS for login. CAS then redirects back here with a
    ticket, which is validated before the user is sent on to the originally
    requested page.
    """
    redirect_url = _cas_url(LOGIN_ROUTE, service=_service_url())

    if 'ticket' in request.args:
        session[TOKEN_KEY] = request.args['ticket']

    if TOKEN_KEY in session:
        if _validate(session[TOKEN_KEY]):
            origin = request.args.get('origin')
            if AFTER_LOGIN_KEY in session:
                redirect_url = session.pop(AFTER_LOGIN_KEY)
            elif origin and _is_local_path(origin):
                redirect_url = origin
            else:
                redirect_url = url_for(current_app.config['CAS_AFTER_LOGIN'])
        else:
            del session[TOKEN_KEY]

    return redirect(redirect_url)


@blueprint.route('/logout/')
def logout():
    """Clears the CAS session data and logs the user out of CAS."""
    for key in (TOKEN_KEY, USERNAME_KEY, ATTRIBUTES_KEY):
        session.pop(key, None)
    return redirect(_cas_url(
        LOGOUT_ROUTE, service=current_app.config.get('CAS_AFTER_LOGOUT')))


class CAS:
    """Registers the CAS routes and exposes the logged-in user."""

    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.config.setdefault('CAS_AFTER_LOGOUT', None)
        app.register_blueprint(blueprint)

    @property
    def username(self):
        return session.get(USERNAME_KEY)

    @property
    def attributes(self):
        return session.get(ATTRIBUTES_KEY)


def login_required(function):
    """Redirects to CAS login unless the user is already logged in."""
    @wraps(function)
    def wrap(*args, **kwargs):
        if USERNAME_KEY not in session:
            session[AFTER_LOGIN_KEY] = request.script_root + request.full_path
            return redirect(url_for('cas.login', _external=True))
        return function(*args, **kwargs)
    return wrap
