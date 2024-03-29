from flask import Markup
from flask import current_app as app
from flask import render_template, request
from werkzeug.exceptions import HTTPException, default_exceptions


def error_handler(error):
    """
    Logs errors and renders specific, if available, or generic error page
    """

    # For 4XX and 5XX level HTTP errors, save specific info
    if isinstance(error, HTTPException):
        code = error.code
        description = error.get_description(request.environ)
        name = error.name

    # For other Exceptions, use general Server error info
    else:
        code = 500
        description = ("<p>We encountered an error "
                       "while trying to fulfill your request</p>")
        name = 'Internal Server Error'

    # Set log level based on error code
    msg = (f'Request \"{request.method} {request.path}\" resulted in: {error}')
    if code >= 500:
        app.logger.error(msg)
    else:
        app.logger.warning(msg)

    # Format specific page, if available (eg. 404), otherwise use generic
    templates_to_try = ['error_{}.html'.format(code), 'error_generic.html']
    return render_template(templates_to_try,
                           code=code,
                           name=Markup(name),
                           description=Markup(description),
                           error=error)


def init_app(app):
    """
    Registers above custom function (error_handler) as error handler
    for any Werkzeug error class, as well as other exceptions
    """
    # Werkzeug, see https://werkzeug.palletsprojects.com/en/1.0.x/exceptions/
    for exception in default_exceptions:
        app.register_error_handler(exception, error_handler)
    # Other exceptions
    app.register_error_handler(Exception, error_handler)
