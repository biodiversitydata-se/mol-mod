#!/usr/bin/env python3

import io
import json
import requests
import subprocess

import pandas as pd
from flask import Blueprint, current_app as app, request
from flask import render_template
from flask import jsonify

from molmod.forms import (BlastResultForm, BlastSearchForm)

from ..config import get_config
CONFIG = get_config()

blast_bp = Blueprint('blast_bp', __name__,
                     template_folder='templates')


@blast_bp.route('/blast', methods=['GET', 'POST'])
def blast():

    sform = BlastSearchForm()
    rform = BlastResultForm()

    # If BLAST was clicked
    if request.form.get('blast_for_seq') and sform.validate_on_submit():
        return render_template('blast.html', sform=sform, rform=rform)

    return render_template('blast.html', sform=sform)


@blast_bp.route('/blast_run', methods=['POST'])
def blast_run():

    # Collect BLAST cmd items into list
    cmd = ['blastn']  # [sform.blast_algorithm.data]
    cmd += ['-perc_identity', request.form['min_identity']]
    cmd += ['-qcov_hsp_perc', request.form['min_qry_cover']]
    cmd += ['-db', app.config['BLAST_DB']]
    # cmd += ['-db', 'fake-path-to-no-db']
    names = ['qacc', 'sacc', 'pident', 'qcovhsp', 'evalue']
    cmd += ['-outfmt', f'6 {" ".join(names)}']
    # Only report x best High Scorting Pair(s) per sequence hit
    # cmd += ['-max_hsps', '1']
    cmd += ['-num_threads', '4']

    # Spawn system process (BLAST) and direct data to file handles
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        # Send seq from sform to stdin, read output & error until 'eof'
        blast_stdout, stderr = process.communicate(
            input=request.form['sequence'].encode()
        )
        # Get exit status
        returncode = process.returncode
        returntxt = translate_returncode(returncode)

        # If BLAST worked (no error)
        if returncode == 0:
            app.logger.debug(f'BLAST returned {returntxt}')

            # Make in-memory file-like string from blast-output
            with io.StringIO(blast_stdout.decode()) as stdout_buf:
                # Read into dataframe
                df = pd.read_csv(
                    stdout_buf, sep='\t', index_col=None,
                    header=None, names=names
                )

                # If no hits
                if len(df) == 0:
                    return jsonify({"data": []})

                # If some hit(s)
                else:
                    # Set single decimal for Sci not & float
                    df['evalue'] = df['evalue'].map('{:.1e}'.format)
                    df = df.round(1)
                    # Print taxonomy on new line
                    df['sacc'] = df['sacc'].str.replace(';', '|')
                    # Extract asvid from sacc = id + taxonomy
                    df['asv_id'] = df['sacc'].str.split('-', expand=True)[0]
                    # Get Subject sequence via ID
                    sdict = get_sseq_from_api(df['asv_id'].tolist())
                    if sdict:
                        app.logger.debug(f'{len(sdict)} '
                                         'unique sequences returned från API')
                        df['asv_sequence'] = df['asv_id'].map(sdict)
                        return jsonify({'data': df.to_dict('records')})
                    app.logger.error('No sequences returned från API')

        # If BLAST error
        else:
            app.logger.error(f'BLAST returned {returntxt} {stderr.decode()}')

    # If error: Return '' instead of None, to avoid logging Werkzeug stack
    # (visible on next request for some reason).
    # jQuery will display custom error msg
    return ''


def get_sseq_from_api(asv_ids: list = []):
    ''' Requests Subject sequences from API,
        as these are not available in regular BLAST response'''
    url = f"{CONFIG.POSTGREST}/rpc/app_seq_from_id"
    payload = json.dumps({'idsx': asv_ids})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        response.raise_for_status()
    except (requests.exceptions.RequestException, Exception) as e:
        app.logger.error(f'API request for subject sequences returned: {e}')
    else:
        sdict = {item['asv_id']: item['asv_sequence']
                 for item in json.loads(response.text)}
        return sdict


def translate_returncode(returncode):
    error_dict = {
        0: "Success",
        1: "Error in query sequence(s) or BLAST options",
        2: "Error in BLAST database",
        3: "Error in BLAST engine",
        4: "Out of memory",
        5: "Network error connecting to NCBI to fetch sequence data",
        6: "Error creating output files",
        255: "Unknown error"
    }
    return error_dict[returncode]
