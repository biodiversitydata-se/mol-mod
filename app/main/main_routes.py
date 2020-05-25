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

    # if request.form.get('search_api'):
    #     sel_fw_prim = request.form.getlist('fw_prim_sel')
    #     return sel_fw_prim[0]
    #     return render_template('blast.html', sform=sform)

    # Get disctint gene-primer rows from db
    response = requests.get('http://localhost:3000/app_dist_primers_genes')
    mixs = json.loads(response.text)
    df = pd.DataFrame(mixs)

    # Get dummy df for testing with multiple primer options
    df = pd.DataFrame({'pcr_primer_name_forward': {0: '341F', 1: 'CYA106F', 2: 'ITS1F'}, 'pcr_primer_name_reverse': {0: '805R', 1: 'CYA781R', 2: 'ITS4B'}, 'pcr_primer_forward': {0: 'CCTACGGGNGGCWGCAG', 1: 'CGGACGGGTGAGTAACGCGTGA', 2: 'CTTGGTCATTTAGAGGAAGTAA'},
                       'pcr_primer_reverse': {0: 'GACTACHVGGGTATCTAATCC', 1: 'GACTACTGGGGTATCTAATCCCATT', 2: 'CAGGAGACTTGTACACGGTCCAG'}, 'target_gene': {0: '16S rRNA', 1: '16S rRNA', 2: 'ITS'}, 'target_subfragment': {0: 'V3-V4', 1: 'V3-V4', 2: 'ITS'}})

    # Add primer display values
    df['fw_show'] = df['pcr_primer_name_forward'] + ': ' + df['pcr_primer_forward']
    df['rv_show'] = df['pcr_primer_name_reverse'] + ': ' + df['pcr_primer_reverse']

    tg_df = df[['target_gene', 'target_gene']].drop_duplicates()
    fw_df = df[['pcr_primer_name_forward', 'fw_show']].drop_duplicates()
    rv_df = df[['pcr_primer_name_reverse', 'rv_show']].drop_duplicates()

    sform.gene_sel.choices = [tuple(x) for x in tg_df.to_numpy()]
    sform.fw_prim_sel.choices = [tuple(y) for y in fw_df.to_numpy()]
    sform.rv_prim_sel.choices = [tuple(z) for z in rv_df.to_numpy()]

    return render_template('search_api.html', sform=sform)


@main_bp.route('/list_asvs', methods=['GET'])
def list_asvs():
    response = requests.get('http://localhost:3000/app_asv_tax_seq')
    asvs = json.loads(response.text)
    return render_template('list_asvs.html', asvs=asvs)


@main_bp.route('/<page_name>')
def other_page(page_name):
    return render_template('index.html', error_page=f'{page_name!r}')
