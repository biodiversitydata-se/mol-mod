"""
This module contains routes involved in blast processing and
result display. The blast-worker containers are called from the
/blast_run endpoint in this module.
"""
import json

import requests
from flask import Blueprint
from flask import current_app as APP
from flask import jsonify, render_template, request
from flask_cas import login_required
from forms import BlastResultForm, BlastSearchForm

from config import get_config

CONFIG = get_config()

blast_bp = Blueprint('blast_bp', __name__,
                     template_folder='templates')


@blast_bp.route('/blast', methods=['GET', 'POST'])
@login_required
def blast():
    """Displays both blast search and result forms. The result table is
       populated on submit via (DataTables) AJAX call to '/blast_run',
       which in turn calls a blast-worker container.
    """

    # Create forms from classes in forms.py
    sform = BlastSearchForm()
    rform = BlastResultForm()

    # Only include result form if BLAST button was clicked
    if request.form.get('blast_for_seq') and sform.validate_on_submit():
        return render_template('blast.html', sform=sform, rform=rform)
    return render_template('blast.html', sform=sform)


@blast_bp.route('/blast_run', methods=['POST'])
@login_required
def blast_run():
    """
    Sends blast run request to one of the available blast workers, and then
    adds subject sequences to the output, via a separate function, and returns
    a JSON Response (or an empty string if error occurs).
    """

    form = dict(request.form.lists())
    form['db'] = CONFIG.BLAST_DB
    response = requests.post('http://blast-worker:5000/', json=form)
    if not response.ok:
        APP.logger.error('Error response returned from worker')
        # If error: Return '' instead of None, to avoid logging Werkzeug stack
        # (visible on next request for some reason).
        # jQuery will display custom error msg
        return ''

    #
    # If there are results, format them and add subject sequence before
    # returning.
    #

    results = response.json()
    results = results['data'] if 'data' in results else results

    # Limit results sent to browser to max 1000 rows
    results = results[0:1000]

    # Format result fields
    for result in results:
        # Set single decimal for Sci not & float
        result['evalue'] = f'{result["evalue"]:.1e}'
        # Set identity and coverage as single decimal floats
        result['pident'] = f'{result["pident"]:.1f}'
        result['qcovhsp'] = f'{result["qcovhsp"]:.1f}'

        # Print taxonomy on new line
        result['stitle'] = result['stitle'].replace(';', '|')
        # Extract asvid from stitle = id + taxonomy
        result['asv_id'] = result['stitle'].split('-')[0]

    # Get Subject sequence via ID, and add to the results
    asv_ids = [f['asv_id'] for f in results]
    sdict = get_sseq_from_api(asv_ids)

    # If no, or incomplete set of, sequences were retrieved,
    # don't show any result rows at all
    if sdict is None:
        APP.logger.error('No sequences were returned from DB')
        return ''
    else:
        for result in results:
            if result['asv_id'] in sdict:
                result['asv_sequence'] = sdict[result['asv_id']]
            else:
                APP.logger.error(f"No seq found for {result['asv_id']}")
                return ''

    return jsonify(data=results)


def get_sseq_from_api(asv_ids: list) -> dict:
    """ Requests Subject sequences from API,
        as these are not available in regular BLAST response"""

    # Send API request
    url = f"{CONFIG.POSTGREST}/rpc/app_seq_from_id"
    payload = json.dumps({'ids': asv_ids})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
    except Exception as ex:
        APP.logger.error('API request for subject sequences returned: %s', ex)
        return None
    else:
        sdict = {item['asv_id']: item['asv_sequence']
                 for item in json.loads(response.text)}
        return sdict
