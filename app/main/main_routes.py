#!/usr/bin/env python

import csv
import json
import io
from io import StringIO
import random
import subprocess
from subprocess import check_output

from flask import Blueprint, flash, make_response, render_template
from flask import jsonify, redirect, url_for
import pandas as pd
import requests
from flask import request
from tabulate import tabulate
from werkzeug.exceptions import HTTPException

from app.forms import BlastSearchForm, BlastResultForm, ApiSearchForm

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    return render_template('about.html')


@main_bp.route('/blast', methods=['GET', 'POST'])
def blast():

    sform = BlastSearchForm()
    rform = BlastResultForm()

    # If BLAST was clicked, and settings are valid
    if request.form.get('blast_for_seq') and sform.validate_on_submit():

        # Collect BLAST cmd items into list
        cmd = ['blastn']  # [sform.blast_algorithm.data]
        cmd += ['-perc_identity', str(sform.min_identity.data)]
        cmd += ['-qcov_hsp_perc', str(sform.min_qry_cover.data)]
        blast_db = 'app/data/blastdb/asvdb'
        cmd += ['-db', blast_db]
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

                    df['sacc'] = df['sacc'].str.replace(';', '|')

                    # Extract asvid from sacc = id + taxonomy
                    df['asv_id'] = df['sacc'].str.split(':', expand=True)[0]

                    # Show both search and result forms on same page
                    return render_template('blast.html', sform=sform, rform=rform, rdf=df)

        # If BLAST error
        else:
            msg = 'Error, the BLAST query was not successful.'
            flash(msg, category='error')

            # Logging the error - Not sure if this is working
            print('BLAST ERROR, cmd: {}'.format(cmd))
            print('BLAST ERROR, returncode: {}'.format(returncode))
            print('BLAST ERROR, output: {}'.format(blast_stdout))
            print('BLAST ERROR, stderr: {}'.format(stderr))

    # If no valid submission (or no hits), show search form (incl. any error messages)
    return render_template('blast.html', sform=sform)


@main_bp.route('/search_api', methods=['GET', 'POST'])
def search_api():

    sform = ApiSearchForm()

    # if request.form.get('search_for_asv'):
    #     sel_fw_prim = request.form.getlist('fw_prim_sel')
    #     return sel_fw_prim[0]

    # Get disctint gene-primer rows from db
    response = requests.get('http://localhost:3000/app_prim_per_gene')
    mixs = json.loads(response.text)
    df = pd.DataFrame(mixs)

    tg_df = df[['gene', 'gene']].drop_duplicates()
    fw_df = df[['fw_display', 'fw_display']].drop_duplicates()
    rv_df = df[['fw_display', 'rv_display']].drop_duplicates()

    sform.gene_sel.choices = [tuple(x) for x in tg_df.to_numpy()]
    sform.fw_prim_sel.choices = [tuple(y) for y in fw_df.to_numpy()]
    sform.rv_prim_sel.choices = [tuple(z) for z in rv_df.to_numpy()]

    return render_template('search_api.html', sform=sform)


@main_bp.route('/get_primers/<gene>/<dir>')
def get_primers(gene, dir):
    col = 'fw_name, fw_display'
    url = f'http://localhost:3000/app_prim_per_gene?select={col}'
    if gene != 'all':
        url += f'&gene=in.({gene})'

    # Get disctint gene-primer rows from db
    response = requests.get(url)
    mixs = json.loads(response.text)
    sel_primers = [{'name': x['fw_name'], 'display': x['fw_display']} for x in mixs]

    return jsonify(sel_primers)


@main_bp.route('/list_asvs', methods=['GET'])
def list_asvs():
    response = requests.get('http://localhost:3000/app_asv_tax_seq')
    asvs = json.loads(response.text)
    return render_template('list_asvs.html', asvs=asvs)


@main_bp.route('/<page_name>')
def other_page(page_name):
    return render_template('index.html', error_page=f'{page_name!r}')
