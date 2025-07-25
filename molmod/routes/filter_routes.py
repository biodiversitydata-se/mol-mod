"""
This module contains routes involved in filter search and result display.
"""
import json

import requests
from flask import Blueprint
from flask import current_app as APP
from flask import render_template, request
from forms import FilterResultForm, FilterSearchForm

from config import get_config
from molmod import custom_login_required

CONFIG = get_config()

filter_bp = Blueprint('filter_bp', __name__,
                      template_folder='templates')


@filter_bp.route('/filter', methods=['GET', 'POST'])
@custom_login_required
def filter():
    """Displays both filter search and result forms. Search form dropdowns
       are populates via (Select2) AJAX call to '/request_drop_options/';
       result tables on submit via (DataTables) AJAX call to '/filter_run'.
    """

    # Create forms from classes in forms.py
    sform = FilterSearchForm()
    rform = FilterResultForm()

    # Reapply any dropdown selections after FILTER submit
    filters = [f.name for f in sform if f.type == 'SelectMultipleField']
    for f in filters:
        selected = [(x, x) for x in request.form.getlist(f) if x]
        if selected:
            sform[f].choices = selected
            APP.logger.debug(f'Reapplied selections: {f}: {selected}')

    # Only include result form if FILTER button was clicked
    if request.form.get('filter_asvs'):
        return render_template('filter.html', sform=sform, rform=rform)
    return render_template('filter.html', sform=sform)


@filter_bp.route('/request_drop_options/<field>', methods=['POST'])
@custom_login_required
def request_drop_options(field) -> dict:
    """Forwards (Select2) AJAX request for filtered dropdown options
    (see main.js) to API, and returns paginated data in dict with Select2
    -specific format."""

    # Make dict of selected list values while renaming list keys,
    # e.g. 'kingdom[]' to 'kingdom'
    payload = {k.replace('[]', ''): request.form.getlist(k)
               for k, v in request.form.items() if k.replace('[]', '')
               # Exclude non-list form items, as .getlist is not applicable,
               # and current field, to allow multiple selections in list
               # (otherwise, first selection removes all other options)
               not in ['term', 'page', field]}

    # Clean search term from special characters that cause errors
    term = request.form['term']
    term = ''.join(e for e in term if e not in '!()?*')

    # Add name of field to be filtered, and (user-typed search) term
    payload.update({'field': field, 'term': term})
    # Add pagination data.
    limit = 25
    offset = (int(request.form['page']) - 1) * limit
    # Examples (assuming more=TRUE, see below):
    # 1) User opens dropdown -> select2 sends page=1 -> offset = 0 -> get
    # records 1-25 from db
    # 2) User scrolls past limit -> page = 2 -> offset = 25 -> get 26-50
    payload.update({'nlimit': limit, 'noffset': offset})

    #
    # Send API request
    #

    # Data are sent to a stored db procedure (app_drop_options) which,
    # in turn, dynamically filters data from a db view (app_filter_mixs_tax),
    # based on target field, typed input and selections made in
    # other dropdowns (see db/db-api-schema.sql)
    url = f"{CONFIG.POSTGREST}/rpc/app_drop_options"
    payload = json.dumps(payload)
    APP.logger.debug(f'Payload sent to /rpc/app_drop_options: {payload}')
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
    except Exception as e:
        APP.logger.error(f'API request for select options resulted in: {e}')
    else:
        # Repackage data into custom format for Select2 boxes
        results = json.loads(response.text)[0]['data']['results']
        count = json.loads(response.text)[0]['data']['count']
        if count > limit:
            # Remove extra record used for pagination check
            results = results[:-1]
        # APP.logger.debug(f"Offset: {offset}, Limit: {limit}, Count: {count}")
        # APP.logger.debug(f"More results: {count > limit}")
        return {'results': results,
                # Enable scrolling if there are at least one additional record
                'pagination': {'more': count > limit}}


@filter_bp.route('/filter_run', methods=['POST'])
@custom_login_required
def filter_run() -> dict:
    """Composes API request for filtered ASV occurrences, based on data
       received in (DataTable) AJAX request, and returns dict
       with DataTables-specific format"""

    # Set base URL for API search
    url = f"{CONFIG.POSTGREST}/app_search_mixs_tax"

    #
    # Append row filters based on POST:ed dropdown selections
    #

    filters = [f for f in request.form if f != 'csrf_token']
    selections = {f: ','.join(
        map(str,request.form.getlist(f))) for f in filters}
    query_parts = []
    for filter, value in selections.items():
        query_parts.append(f'{filter}=in.({value})')
    query_parts.append('limit=1000')

    url += '?' + '&'.join(query_parts)
    # APP.logger.debug(f'URL for API request: {url}')

    #
    # Send API request
    #

    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
        APP.logger.error(f'API request for filtered occurences returned: {e}')
    else:
        results = json.loads(response.text)
        # APP.logger.debug(results)
        return {"data": results}
