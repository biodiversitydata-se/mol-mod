import json
import os
from datetime import datetime as dt

import requests
from flask import (
    Blueprint, abort, current_app as APP, render_template,
    request, send_from_directory, session, url_for)
from flask_mail import Message
from forms import DownloadForm, UploadForm
from werkzeug.utils import secure_filename

from config import get_config
from molmod import custom_login_required

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


def get_stats() -> dict:
    """Makes API request for db stats, and returns dict."""

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
@custom_login_required
def upload():
    """Checks whether logged-in user has required role (UPLOAD_ROLE) for file
       upload. Authorized users are sent to upload page; unauthorized users to
       custom 403 Forbidden page. Selected files currently need to pass
       validation in both forms.py and js, the latter of which was added to be
       able to reject larger files faster, and to avoid getting 413 response
       directly from nginx.
    """

    # Get CAS user roles from session
    cas_attributes = session.get('CAS_ATTRIBUTES', None)

    # login_required should mean we're authenticated, but check this
    if not cas_attributes:
        abort(403)

    roles = cas_attributes['cas:authority'].split(',')

    APP.logger.debug(
        f'User has CAS roles: {roles} ')

    # Stop unauthorized users
    if CONFIG.UPLOAD_ROLE not in roles:
        abort(403)

    form = UploadForm()

    if request.method != 'POST':
        return render_template('upload.html', form=form, upload_error=False)

    # User has tried to submit file (POST)
    # Check if it passes (simple) validation in forms.py
    if not form.validate_on_submit():
        return render_template('upload.html', form=form)

    # Get filename
    f = form.file.data
    filename = secure_filename(f.filename)
    # Add user email & time
    email = cas_attributes['cas:email']
    upload_time = dt.now().strftime("%y%m%d-%H%M%S")
    ext_filename = email + '_' + upload_time + '_' + filename

    dir = '/app/data-volumes/uploads'
    if not os.path.exists(dir):
        os.makedirs(dir)
    try:
        f.save(os.path.join(dir, ext_filename))
    except Exception as ex:
        APP.logger.error(f'File {ext_filename} could not be saved due to {ex}')
    else:
        APP.logger.info(f'Successfully uploaded file {ext_filename}')

        # Notify admin
        msg = Message('New file upload',
                      sender=APP.mail.username,
                      recipients=CONFIG.UPLOAD_EMAIL)
        msg.body = f"""
        Hello SBDI-MOL colleagues,

        A new file has been uploaded to the ASV portal:

        Provider email: {email}
        Upload time: {upload_time}
        Original filename: {filename}
        Saved as: {ext_filename}

        Have a nice day!

        / Swedish ASV portal
        """
        try:
            APP.mail.send(msg)
        except Exception as ex:
            APP.logger.error(f"Could not send upload notification due to {ex}")
        else:
            APP.logger.info('Successfully sent upload notification.')
            # Display 'success page' only if upload AND notification worked
            return render_template('uploaded.html', filename=filename)

    # Display error msg if EITHER upload OR email failed, so that data
    # providers get a chance to tell us about uploaded files
    return render_template('upload.html', form=form, upload_error=True)


@main_bp.route('/submit')
def submit():
    # abort(301)
    return render_template('submit.html')


@main_bp.route("/files/<filename>")
def files(filename):
    """Downloads a file without requiring log-in"""

    dir = os.path.join('.', 'static', 'downloads')
    try:
        return send_from_directory(dir, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)


@main_bp.route("/datasets/<filename>", methods=['GET'])
@custom_login_required
def datasets(filename):
    """Downloads a (log-in protected) dataset file"""
    APP.logger.info(f"Requested download of {filename}")
    dir = '/app/data-volumes/exports'
    try:
        return send_from_directory(dir, filename, as_attachment=True)
    except Exception as e:
        APP.logger.error(f"Failed download of {filename} due to {e}")
        abort(404)


@main_bp.route("/download", methods=['GET'])
@custom_login_required
def download():
    """Lists available datasets"""
    ds = list_datasets()

    # Create forms from classes in forms.py
    dlform = DownloadForm()

    return render_template('download.html', dlform=dlform, rows=ds)


@main_bp.route('/list_datasets', methods=['GET'])
@custom_login_required
def list_datasets() -> dict:
    """Composes API request for available datasets, based on data
       received in (DataTable) AJAX request, and returns dict
       with DataTable-specific format"""

    url = f"{CONFIG.POSTGREST}/app_dataset_list"

    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
        APP.logger.error(f'API request for dataset list returned: {e}')
    else:
        results = json.loads(response.text)  # -> list of dicts
        for ds in results:
            # Only add IPT link if ID was provided
            if ds['ipt_resource_id']:
                ds['ipt_link'] = (CONFIG.IPT_BASE_URL + '/resource?r='
                                  + ds['ipt_resource_id'])
            else:
                msg = f'Dataset {ds["dataset_id"]} has no IPT resource ID'
                APP.logger.warning(msg)
            # Only add Download link if zip exists
            zip_path = os.path.join('/app/data-volumes/exports',
                                    f'{ds["dataset_id"]}.zip')

            if os.path.isfile(zip_path):
                ds['zip_link'] = url_for('main_bp.datasets',
                                         filename=f"{ds['dataset_id']}.zip",
                                         _external=True)
            else:
                APP.logger.warning(f'Zip file does not exist: {zip_path}')

        # APP.logger.debug(results)
        return results
