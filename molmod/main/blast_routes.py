#!/usr/bin/env python3

import io
import json
import requests
import subprocess

import pandas as pd
from flask import Blueprint, current_app as app, flash, request
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
    names = ['qacc', 'sacc', 'pident', 'qcovhsp', 'evalue']
    cmd += ['-outfmt', f'6 {" ".join(names)}']
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

        # If BLAST worked (no error)
        if returncode == 0:
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
                    df['asv_sequence'] = df['asv_id'].map(sdict)

                    return jsonify({'data': df.to_dict('records')})

        # If BLAST error
        else:
            # Error will be handled by JQuery
            return None


def get_sseq_from_api(asv_ids: list = []):
    ''' Requests Subject sequences from API,
        as these are not available in BLAST response'''
    url = f"{CONFIG.POSTGREST}/rpc/app_seq_from_id"
    payload = json.dumps({'ids': asv_ids})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        sdict = {item['asv_id']: item['asv_sequence']
                 for item in json.loads(response.text)
                 }
        return sdict
    except Exception:
        msg = 'Sorry, but no ASV sequences were successfully returned.'
        flash(msg, category='error')
        return {}
