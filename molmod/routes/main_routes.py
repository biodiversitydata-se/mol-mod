import json
import os

import requests
from flask import Blueprint, abort
from flask import current_app as APP
from flask import render_template, request, send_from_directory, session
from flask_cas import login_required
from molmod.config import get_config
from molmod.forms import UploadForm
from werkzeug.utils import secure_filename

CONFIG = get_config()

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    # abort(301)
    stats = get_stats()
    return render_template('about.html', rows=stats)


@main_bp.route('/stats', methods=['GET'])
def get_stats() -> dict:
    '''Makes API request for db stats, and returns dict.'''

    url = f"{CONFIG.POSTGREST}/app_about_stats"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
        APP.logger.error(f'API request for db stats returned: {e}')
    else:
        results = json.loads(response.text)
        # APP.logger.debug(results)
        return results


@main_bp.route('/upload', methods=['GET', 'POST'])
# Redirect user to Bioatlas CAS login
@login_required
def upload():
    '''Checks whether logged-in user has required role for file upload.
       Authorized users are sent to upload page; unauthorized users to custom
       403 Forbidden page ('Data upload' menu item is actually hidden for those
       - see __init.py__ + banner.html - but 403 is used if unauthorized user
       types in '/upload' url).

       Standard Bioatlas users have role 'ROLE_USER', and we require
       'ROLE_COLLECTION_ADMIN' for upload, for now, but will have a specific
       molmod-upload role added later.
    '''

    # Get CAS user roles from session
    cas_attributes = session.get('CAS_ATTRIBUTES', None)

    # login_required should mean we're authenticated, but check this
    if not cas_attributes:
        abort(403)

    roles = cas_attributes['cas:authority'].split(',')
    APP.logger.debug(
        f'User has CAS roles: {roles} ')

    # Stop unauthorized users
    if os.getenv('UPLOAD_ROLE') not in roles:
        abort(403)

    form = UploadForm()

    if request.method != 'POST':
        return render_template('upload.html', form=form, upload_error=False)

    # User has tried to submit file (POST)
    # Check if it passes (simple) validation in forms.py
    if not form.validate_on_submit():
        return render_template('upload.html', form=form, upload_error=True)

    # Get filename
    f = form.file.data
    filename = secure_filename(f.filename)
    # Save file, or report error
    try:
        f.save(os.path.join(CONFIG.UPLOAD_PATH, filename))
    except Exception as err:
        # Display error msg in upload form
        APP.logger.error(
            f'File {filename} could not be saved due to {err}')
        return render_template('upload.html', form=form, upload_error=True)

    APP.logger.info(f'Uploaded file {filename}')
    return render_template('uploaded.html', filename=filename)


@main_bp.route('/submit')
def submit():
    # abort(301)
    return render_template('submit.html')


@main_bp.route("/files/<filename>")
def files(filename):
    """Downloads a file"""
    dir = os.path.join('.', 'static', 'downloads')
    if not os.path.exists(dir):
        os.makedirs(dir)
    try:
        return send_from_directory(dir, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)
