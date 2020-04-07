#!/usr/bin/env python

import csv
import json
import io
from io import StringIO
import subprocess
from subprocess import check_output

from flask import Blueprint, flash, make_response, render_template
from flask import redirect, url_for
import pandas as pd
import requests
from tabulate import tabulate

from app.forms import BlastFilterForm

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/blast', methods=['GET', 'POST'])
def blast():
    form = BlastFilterForm()
    if form.validate_on_submit():
        cmd = ['blastn']  # [form.blast_algorithm.data]

        e_val = int(form.e_value_factor.data) * 10**int(form.e_value_exponent.data)
        cmd += ["-evalue", str(e_val)]

        if form.blast_algorithm.data == 'blastp':
            blast_db = "app/data/blastdb/asvdb"
        else:
            blast_db = "app/data/blastdb/asvdb"

        cmd += ['-db', blast_db]
        # names = ["qseqid", "sseqid", "pident", "qlen", "slen", "length", "qcovs",
        #          "qcovhsp", "mismatch", "gapopen", "evalue", "bitscore"]
        names = ['qacc', 'sacc', 'pident', 'length', 'evalue']

        cmd += ['-outfmt', f'6 {" ".join(names)}']

        # Spawn system process and direct data to file handles
        with subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            # Send seq from form to stdin, read output & error until eof
            blast_stdout, stderr = process.communicate(input=form.sequence.data.encode())
            # Get exit status
            returncode = process.returncode
        # If OK
        if returncode == 0:
            # Make in-memory file-like str from blast-output
            with io.StringIO(blast_stdout.decode()) as stdout_buf:
                # Read into dataframe
                df = pd.read_csv(stdout_buf, sep='\t', index_col=None, header=None, names=names)

                df['sacc'] = df['sacc'].str.replace(':', '\\n')
                # Use 1 decimal for sci-num evalue
                df['evalue'] = df['evalue'].map('{:.1e}'.format)

                # Filter on identity and alignment length
                df = df[df['pident'] >= form.min_identity.data]
                hits_after_pident = len(df)

                df = df[df['length'] >= form.min_aln_length.data]
                hits_after_length = len(df)

                # Fetch counts for the matching genes
                if len(df) == 0:
                    msg = "No hits were found in the BLAST search"
                    # flash(msg, category="error")
                    return msg

                # .to_html())
                df_html = df.to_html(classes="table table-striped",
                                     index=False).replace("\\n", "<br>")

                return render_template('blast.html',  form=form, result=df_html, title='Blast results')

        msg = "Error, the BLAST query was not successful."
        flash(msg, category="error")

        # Logging the error
        print("BLAST ERROR, cmd: {}".format(cmd))
        print("BLAST ERROR, returncode: {}".format(returncode))
        print("BLAST ERROR, output: {}".format(blast_stdout))
        print("BLAST ERROR, stderr: {}".format(stderr))

    return render_template('blast.html', form=form)


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
