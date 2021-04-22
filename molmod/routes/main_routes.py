import json
import os

import requests
from flask import Blueprint, abort
from flask import current_app as APP
from flask import render_template, send_from_directory
from molmod.config import get_config

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
