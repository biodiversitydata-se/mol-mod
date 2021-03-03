import os

from flask import Blueprint
from flask import current_app as APP
from flask import render_template, request
from flask_cas import login_required
from molmod import cas
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
@login_required
def upload():

    roles = cas.attributes['cas:authority'].split(',')
    if os.getenv('UPLOAD_ROLE') not in roles:
        return render_template('upload_refused.html')

    form = UploadForm()
    msg = ''
    if request.method == 'POST':
        if form.validate_on_submit() and True:
            f = form.file.data
            filename = secure_filename(f.filename)
            try:
                f.save(os.path.join(CONFIG.UPLOAD_PATH, filename))
            except Exception as err:
                msg = 'Sorry, something unexpected happened during file '\
                      'upload. Please, contact support if this error persists!'
                APP.logger.error(
                    f'File {filename} could not be saved due to {err}')
            else:
                APP.logger.info(f'Uploaded file {filename}')
                return render_template('uploaded.html', filename=filename)
    return render_template('upload.html', form=form, msg=msg)
