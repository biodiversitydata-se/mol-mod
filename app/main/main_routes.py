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


'''Test of ALA POST'''
@main_bp.route('/form', methods=["GET"])
def form():
    return '''
        <form name="taxaUploadForm" id="taxaUploadForm"
            action="https://records.bioatlas.se/ws/occurrences/batchSearch"
                method="POST">
            <div class="row">
                <div class="col-sm-8">
                    <div class="form-group">
                        <label for="raw_names">Enter a list of taxon names/scientific names, one name per line (common names not currently supported).</label>
                        <br><textarea name="queries" id="raw_names" class="form-control" rows="15" cols="60">Bombus</textarea>
                    </div>
                    <input type="hidden" name="redirectBase"
                           value="https://records.bioatlas.se/occurrences/search" class="form-control">
                    <input type="hidden" name="field" value="raw_name" class="form-control"/>
                    <input type="hidden" name="action" value="Search" />
                    <input type="submit"
                           value="Search" class="btn btn-primary" />
                </div>
            </div>
        </form>'''


@main_bp.route('/blast', methods=['GET', 'POST'])
def blast():

    sform = BlastSearchForm()
    rform = BlastResultForm()

    # If Search was clicked, and settings are valid
    if request.form.get('blast_for_seq') and sform.validate_on_submit():

        # Collect BLAST cmd items into list
        cmd = ['blastn']  # [sform.blast_algorithm.data]
        e_val = int(sform.e_value_factor.data) * 10**int(sform.e_value_exponent.data)
        cmd += ["-evalue", str(e_val)]
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
                    # Filter not available as blast cmd option...?
                    df = df[df['length'] >= sform.min_aln_length.data]  # Show 1 decimal

                    df['evalue'] = df['evalue'].map('{:.1e}'.format)
                    df = df.round(1)

                    df['asvid'] = df['sacc'].str.split(":", expand=True)[0]

                    return render_template('blast.html',  sform=sform, rform=rform, rdf=df)

        # If BLAST error
        else:
            msg = "Error, the BLAST query was not successful."
            flash(msg, category="error")

            # Logging the error FUNKAR DETTA?
            print("BLAST ERROR, cmd: {}".format(cmd))
            print("BLAST ERROR, returncode: {}".format(returncode))
            print("BLAST ERROR, output: {}".format(blast_stdout))
            print("BLAST ERROR, stderr: {}".format(stderr))

    # If Show was clicked (add validation of non-zero selection later)
    if request.form.get('show_occur') and rform.validate_on_submit():
        # Get selected hits from form
        ids = request.form.getlist("asvid")

        # Make url query string
        idstr = '%22%20OR%20taxon_name%3A%22'.join([str(id) for id in ids])
        url = 'http://molecular.infrabas.se/ala-hub/occurrences/search?q=(taxon_name%3A%22' + \
            idstr + '%22)#tab_recordsView'

        # Redirect to SBDI / bioatlas (GET request)
        return redirect(url)

    # If nothing has been submitted (or no hits were found)
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
