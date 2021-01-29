"""
This module contains the routes that are involved in blast processing and
annotation. The blast-worker containers are called from the /blast_run endpoint
in this module.
"""
import json

import requests

from flask import Blueprint, current_app as app, request
from flask import render_template
from flask import jsonify

# pylint: disable=import-error
from molmod.forms import (BlastResultForm, BlastSearchForm)
from molmod.config import get_config

CONFIG = get_config()

blast_bp = Blueprint('blast_bp', __name__,
                     template_folder='templates')


@blast_bp.route('/blast', methods=['GET', 'POST'])
def blast():
    '''Displays both blast search and result forms. Result table is
       populated on submit via (DataTables) AJAX call to '/blast_run'.
    '''

    sform = BlastSearchForm()
    rform = BlastResultForm()

    # Only include result form if BLAST button was clicked
    if request.form.get('blast_for_seq') and sform.validate_on_submit():
        return render_template('blast.html', sform=sform, rform=rform)
    return render_template('blast.html', sform=sform)


@blast_bp.route('/blast_run', methods=['POST'])
def blast_run():
    """
    Sends the blast run request to one of the available blast workers, and then
    adds subject sequences to the output, via a separate function, and returns
    a JSON Response (or an empty string if error occurs).
    """

    # convert to json to be able to manipulate the data

    form = dict(request.form.lists())
    form['db'] = app.config['BLAST_DB']
    response = requests.post('http://blast-worker:5000/', json=form)
    if not response.ok:
        app.logger.error(response.text)
        # If error: Return '' instead of None, to avoid logging Werkzeug stack
        # (visible on next request for some reason).
        # jQuery will display custom error msg
        return ''

    # If there are results, format them and add subject sequence before
    # returning.

    results = response.json()
    results = results['data'] if 'data' in results else results

    # format result fields
    for result in results:
        # Set single decimal for Sci not & float
        result['evalue'] = f'{result["evalue"]:.1e}'
        # set identity and coverage as single decimal floats
        result['pident'] = f'{result["pident"]:.1f}'
        result['qcovhsp'] = f'{result["qcovhsp"]:.1f}'

        # Print taxonomy on new line
        result['sacc'] = result['sacc'].replace(';', '|')
        # Extract asvid from sacc = id + taxonomy
        result['asv_id'] = result['sacc'].split('-')[0]

    # Get Subject sequence via ID, and add them to the results
    asv_ids = [f['asv_id'] for f in results]
    sdict = get_sseq_from_api(asv_ids)
    for result in results:
        if result['asv_id'] in sdict:
            result['asv_sequence'] = sdict[result['asv_id']]

    return jsonify(data=results)


def get_sseq_from_api(asv_ids: list) -> dict:
    ''' Requests Subject sequences from API,
        as these are not available in regular BLAST response'''

    # Send API request
    url = f"{CONFIG.POSTGREST}/rpc/app_seq_from_id"
    payload = json.dumps({'ids': asv_ids})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as ex:
        app.logger.error('API request for subject sequences returned: %s', ex)
    else:
        sdict = {item['asv_id']: item['asv_sequence']
                 for item in json.loads(response.text)}
        return sdict
