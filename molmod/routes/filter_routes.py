import json

import requests
from flask import Blueprint, current_app as app
from flask import render_template, request

from molmod.forms import (FilterResultForm, FilterSearchForm)
from molmod.config import get_config

CONFIG = get_config()

filter_bp = Blueprint('filter_bp', __name__,
                      template_folder='templates')


@filter_bp.route('/filter', methods=['GET', 'POST'])
def filter():
    '''Displays both filter search and result forms. Search form dropdowns
       are populates via (select2) AJAX call to '/request_drop_options/';
       result tables on submit via (DataTables) AJAX call to '/filter_run'.
    '''
    sform = FilterSearchForm()
    rform = FilterResultForm()

    # Reapply any dropdown selections after FILTER submit
    filters = [f.name for f in sform if f.type == 'SelectMultipleField']
    for f in filters:
        selected = [(x, x) for x in request.form.getlist(f) if x]
        if selected:
            sform[f].choices = selected
            app.logger.debug(f'Reapplied selections: {f}: {selected}')

    # Only include result form if FILTER button was clicked
    if request.form.get('filter_asvs'):
        return render_template('filter.html', sform=sform, rform=rform)
    return render_template('filter.html', sform=sform)


@filter_bp.route('/request_drop_options/<field>', methods=['POST'])
def request_drop_options(field):
    '''Forwards (select2) AJAX request for filtered dropdown options to
    postgREST/postgres function, and returns paginated JSON result'''
    # Make dict of posted filters
    # (e.g. selected kingdom(s), received as 'kingdom[]')
    # but exclude current field, to allow multiple choice
    payload = {k.replace('[]', ''): request.form.getlist(k)
               for k, v in request.form.items() if k.replace('[]', '')
               not in ['term', 'page', field]}
    # Add (typed search) term, and field to be filtered, as str
    payload.update({'field': field, 'term': request.form['term']})
    # Add pagination
    limit = 25
    offset = (int(request.form['page']) - 1) * limit
    payload.update({'nlimit': limit, 'noffset': offset})
    url = f"{CONFIG.POSTGREST}/rpc/app_drop_options"
    payload = json.dumps(payload)
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
    except Exception as e:
        app.logger.error(f'API request for select options resulted in: {e}')
    else:
        results = json.loads(response.text)[0]['data']['results']
        count = json.loads(response.text)[0]['data']['count']
        return {'results': results,
                'pagination': {'more': (offset + limit) < count}}


@filter_bp.route('/filter_run', methods=['POST'])
def filter_run():
    '''Composes API request for filtered ASV occurrences, based on data
       received in (DataTable) AJAX request, and returns JSON response'''

    # Set base URL for API search
    url = f"{CONFIG.POSTGREST}/app_search_mixs_tax"

    # Append row filters based on POST:ed dropdown selections
    filters = [f for f in request.form if f != 'csrf_token']
    selections = {f: ','.join(
        map(str, request.form.getlist(f))) for f in filters}
    if selections:
        url += '?'
        for filter, value in selections.items():
            url += f'&{filter}=in.({value})'
    app.logger.debug(f'URL for API request: {url}')

    # Make API request
    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
        app.logger.error(f'API request for filtered occurences returned: {e}')
    else:
        # Convert json to list of dicts
        return {"data": json.loads(response.text)}
