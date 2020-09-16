#!/usr/bin/env python3

import io

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
                    # Set single decimal for Sci not & float
                    df['evalue'] = df['evalue'].map('{:.1e}'.format)
                    df = df.round(1)

                    # Get subject sequence via blastdbcmd
                    seq_df = get_sseq_from_blastdb(df['sacc'])
                    # Perhaps safer to use a left join (rather than condcat) here
                    df['asv_sequence'] = seq_df['asv_sequence']

                    df['sacc'] = df['sacc'].str.replace(';', '|')

                    # Extract asvid from sacc = id + taxonomy
                    df['asv_id'] = df['sacc'].str.split('-', expand=True)[0]

                    rdict = df.to_dict('records')

                    # Show both search and result forms on same page
                    return render_template('blast.html', sform=sform, rform=rform, blast_results=rdict)

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


def get_sseq_from_blastdb(ids):

    id_str = ','.join(ids.to_list())

    cmd = ['blastdbcmd']
    cmd += ['-db', 'misc/blastdb/asvdb']
    cmd += ['-entry', id_str]
    cmd += ['-outfmt', '%a %s']

    # Spawn system process (blastdbcmd) and direct data to file handles
    with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE) as process:
        # Send seq from sform to stdin, read output & error until 'eof'
        blast_stdout, stderr = process.communicate()
        # # Get exit status
        returncode = process.returncode

        # If blastdbcmd worked (no error)
        if returncode == 0:
            # Make in-memory file-like string from blast-output
            with io.StringIO(blast_stdout.decode()) as stdout_buf:
                df = pd.read_csv(stdout_buf, sep=' ', header=None, names=('sacc', 'asv_sequence'))

                # If some hits
                if len(df) > 0:
                    return df
