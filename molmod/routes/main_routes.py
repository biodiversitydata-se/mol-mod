import os

from flask import Blueprint, abort
from flask import current_app as APP
from flask import render_template, request, session
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
    return render_template('about.html')


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
    roles = cas_attributes['cas:authority'].split(',')
    APP.logger.debug(
        f'User has CAS roles: {roles} ')

    # Stop unauthorized users
    if os.getenv('UPLOAD_ROLE') not in roles:
        abort(403)

    # Enable authorized users
    form = UploadForm()
    upload_error = False
    # If user has tried to submit file (POST)
    if request.method == 'POST':
        # If file passes (simple) validation in forms.py
        if form.validate_on_submit():
            # Get filename
            f = form.file.data
            filename = secure_filename(f.filename)
            # Save file, or report error
            try:
                f.save(os.path.join(CONFIG.UPLOAD_PATH, filename))
            except Exception as err:
                # Display error msg in upload form
                upload_error = True
                APP.logger.error(
                    f'File {filename} could not be saved due to {err}')
            else:
                APP.logger.info(f'Uploaded file {filename}')
                return render_template('uploaded.html', filename=filename)
    # Show upload form (GET or POST), with error when applicable (POST only)
    return render_template('upload.html', form=form, upload_error=upload_error)
