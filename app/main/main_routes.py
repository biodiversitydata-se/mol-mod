#!/usr/bin/env python

import csv
import json
import io
from io import StringIO
import random
import subprocess
from subprocess import check_output

from flask import Blueprint, flash, make_response, render_template
from flask import redirect, url_for
import pandas as pd
import requests
from flask import request
from tabulate import tabulate
from werkzeug.exceptions import HTTPException

from app.forms import BlastSearchForm, BlastResultForm

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/blast', methods=['GET', 'POST'])
def blast():

    sform = BlastSearchForm()

    # If Search was clicked, and settings are valid
    if request.form.get('blast_for_seq') and sform.validate_on_submit():

        # Collect BLAST cmd items into list
        cmd = ['blastn']  # [sform.blast_algorithm.data]
        cmd += ["-perc_identity", str(sform.min_identity.data)]
        blast_db = "app/data/blastdb/asvdb"
        cmd += ['-db', blast_db]
        names = ['qacc', 'sacc', 'pident', 'length', 'evalue']
        cmd += ['-outfmt', f'6 {" ".join(names)}']

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
                    msg = "No hits were found in the BLAST search"
                    flash(msg, category="error")

                # If some hit(s)
                else:
                    rform = BlastResultForm()

                    # Filter on alignment length (not available as cmd option...?)
                    df = df[df['length'] >= sform.min_aln_length.data]  # Show 1 decimal

                    # Set single decimal for Sci not & float
                    df['evalue'] = df['evalue'].map('{:.1e}'.format)
                    df = df.round(1)

                    # Extract asvid from sacc = id + taxonomy
                    df['asvid'] = df['sacc'].str.split(":", expand=True)[0]

                    # Show both search and result forms on same page
                    return render_template('blast.html',  sform=sform, rform=rform, rdf=df)

        # If BLAST error
        else:
            msg = "Error, the BLAST query was not successful."
            flash(msg, category="error")

            # Logging the error - Not sure if this is working
            print("BLAST ERROR, cmd: {}".format(cmd))
            print("BLAST ERROR, returncode: {}".format(returncode))
            print("BLAST ERROR, output: {}".format(blast_stdout))
            print("BLAST ERROR, stderr: {}".format(stderr))

    # If no valid submission (or no hits), show search form (incl. any error messages)
    return render_template('blast.html', sform=sform)


@main_bp.route('/about')
def about():
    return redirect(url_for('main_bp.index'))


@main_bp.route('/show_asvs', methods=['GET'])
def show_asvs():
    # Using postgREST API

    response = requests.get('http://localhost:3000/asv_tax_seq')
    asvs = json.loads(response.text)
    return render_template('asvs.html',
                           asvs=asvs,
                           title="ASVs currently in database")


@main_bp.route('/<page_name>')
def other_page(page_name):
    response = make_response(page_name, 404)
    return render_template('404.html', page=f'{page_name!r}')
