#!/usr/bin/env python3

import io
import json
import requests
import subprocess

import pandas as pd
from flask import Blueprint, current_app as app, flash, request
from flask import render_template, url_for

from molmod.forms import (BlastResultForm, BlastSearchForm)

blast_bp = Blueprint('blast_bp', __name__,
                     template_folder='templates')


@blast_bp.route('/blast', methods=['GET', 'POST'])
def blast():

    sform = BlastSearchForm()
    rform = BlastResultForm()

    # If BLAST was clicked, and settings are valid
    if request.form.get('blast_for_seq') and sform.validate_on_submit():

        # Collect BLAST cmd items into list
        cmd = ['blastn']  # [sform.blast_algorithm.data]
        cmd += ['-perc_identity', str(sform.min_identity.data)]
        cmd += ['-qcov_hsp_perc', str(sform.min_qry_cover.data)]
        cmd += ['-db', app.config['BLAST_DB']]
        names = ['qacc', 'sacc', 'pident', 'qcovhsp', 'evalue']
        cmd += ['-outfmt', f'6 {" ".join(names)}']
        cmd += ['-num_threads', '4']
        # default: 59 sec, 4/6/8 - 35 sec ca.

        # Spawn system process (BLAST) and direct data to file handles
        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            # Send seq from sform to stdin, read output & error until 'eof'
            blast_stdout, stderr = process.communicate(input=sform.sequence.data.encode())
            # Get exit status
            returncode = process.returncode

        # If BLAST worked (no error)
        if returncode == 0:
            # Make in-memory file-like string from blast-output
            with io.StringIO(blast_stdout.decode()) as stdout_buf:
                # Read into dataframe
                df = pd.read_csv(stdout_buf, sep='\t', index_col=None, header=None, names=names)

                # If no hits
                if len(df) == 0:
                    msg = 'No hits were found in the BLAST search'
                    flash(msg, category='error')

                # If some hit(s)
                else:
                    # Improve display
                    df['evalue'] = df['evalue'].map('{:.1e}'.format)
                    df = df.round(1)
                    df['sacc'] = df['sacc'].str.replace(';', '|')

                    # Extract asvid from sacc = id + taxonomy
                    df['asv_id'] = df['sacc'].str.split('-', expand=True)[0]

                    # Get Subject sequence (unavailable in blast(n))
                    ndict = get_sseq_from_api(df['asv_id'].tolist())
                    df['asv_sequence'] = df['asv_id'].map(ndict)

                    rjson = df.to_json(orient="records")

                    # Show both search and result forms on same page
                    return render_template('blast.html', sform=sform, rform=rform, blast_results=rjson)

        # If BLAST error
        else:
            msg = 'Sorry, the BLAST query was not successful.'
            flash(msg, category='error')

            # Logging the error - Not sure if this is working
            print('BLAST ERROR, cmd: {}'.format(cmd))
            print('BLAST ERROR, returncode: {}'.format(returncode))
            print('BLAST ERROR, output: {}'.format(blast_stdout))
            print('BLAST ERROR, stderr: {}'.format(stderr))

    # If no valid submission (or no hits), show search form (incl. any error messages)
    return render_template('blast.html', sform=sform)


def get_sseq_from_api(asv_ids: list = []):
    ''' Requests Subject sequences from API, as these are not available in BLAST response'''
    url = "http://localhost:3000/rpc/app_seq_from_id"
    payload = json.dumps({'ids': asv_ids})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        sdict = {item['asv_id']: item['asv_sequence'] for item in json.loads(response.text)}
        return sdict
    except:
        msg = 'Sorry, but ASV sequences were not successfully returned.'
        flash(msg, category='error')
        return {}
