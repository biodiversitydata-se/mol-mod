#!/usr/bin/env python3

import io
import json
import subprocess

import pandas as pd
import requests
from flask import Blueprint, current_app as app, flash, jsonify
from flask import make_response, redirect, render_template, request, url_for
from tabulate import tabulate
from werkzeug.exceptions import HTTPException

from molmod.forms import (ApiResultForm, ApiSearchForm, BlastResultForm,
                          BlastSearchForm)

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


# Temp - for debugging
@main_bp.route('/test')
def test():
    # var = app.config
    var = app.instance_path
    return render_template('test.html', var=var)


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

                    df['sacc'] = df['sacc'].str.replace(';', '|')

                    # Extract asvid from sacc = id + taxonomy
                    df['asv_id'] = df['sacc'].str.split('-', expand=True)[0]

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


def get_drop_options(val_col, disp_col, genes='all'):
    '''Uses gene and/or column names to filter api request for genes or primers,
    and returns sorted list of unique gene/primer value and display text tuples'''
    # Add column filter to url
    url = f'http://localhost:3000/app_prim_per_gene?select={val_col},{disp_col}'
    # Add row/gene filter, if genes have been specified
    if genes != 'all':
        url += f'&gene=in.({genes})'
    # Make api request
    response = requests.get(url)
    # Convert json to list of dicts
    rdict_lst = json.loads(response.text)
    # Get list of unique (set of) value-display tuples
    options = list(set([(x[val_col], x[disp_col]) for x in rdict_lst]))
    # Sort on value
    options.sort(key=lambda x: x[0])
    return options


@main_bp.route('/search_api', methods=['GET', 'POST'])
def search_api():

    sform = ApiSearchForm()
    rform = ApiResultForm()

    # Get dropdown options from api, and send to form
    sform.gene_sel.choices = get_drop_options('gene', 'gene')
    sform.fw_prim_sel.choices = get_drop_options('fw_name', 'fw_display')
    sform.rv_prim_sel.choices = get_drop_options('rv_name', 'rv_display')

    # If SEARCH was clicked
    if request.form.get('search_for_asv'):
        # Set base URL for api search
        url = f'http://localhost:3000/app_asv_mixs'

        # Get selected genes and/or primers
        gene_lst = request.form.getlist('gene_sel')
        fw_lst = request.form.getlist('fw_prim_sel')
        rv_lst = request.form.getlist('rv_prim_sel')
        # Set logical operator
        op = '?'

        # Modify URL according to selections
        if len(gene_lst) > 0:
            genes = ','.join(map(str, gene_lst))
            url += f'?gene=in.({genes})'
            # Use 'AND' for additional criteria, if any
            op = '&'
        if len(fw_lst) > 0:
            fw = ','.join(map(str, fw_lst))
            url += f'{op}fw_name=in.({fw})'
            # Use 'AND' for additional criteria, if any
            op = '&'
        if len(rv_lst) > 0:
            rv = ','.join(map(str, rv_lst))
            url += f'{op}rv_name=in.({rv})'
        # return url
        # Make api request
        response = requests.get(url)
        # Convert json to list of dicts
        rdict_lst = json.loads(response.text)
        df = pd.DataFrame(rdict_lst)

        return render_template('search_api.html', sform=sform, rform=rform, rdf=df)

    return render_template('search_api.html', sform=sform)


@main_bp.route('/get_primers/<genes>/<dir>')
def get_primers(genes, dir):
    '''Takes gene and/or direction from url in Ajax request, and uses
    function to make api request, returning primer options as json'''
    val_col = f'{dir}_name'
    disp_col = f'{dir}_display'
    # Get list of primer name & display text tuples from api
    prim_tpl_lst = get_drop_options(val_col, disp_col, genes)
    # Add keys to make list of dict
    prim_dct_lst = [dict(zip(['name', 'display'], val)) for val in prim_tpl_lst]
    return jsonify(prim_dct_lst)

# Perhaps use for third option on start page
# @main_bp.route('/list_asvs', methods=['GET'])
# def list_asvs():
#     response = requests.get('http://localhost:3000/app_asv_tax_seq')
#     asvs = json.loads(response.text)
#     return render_template('list_asvs.html', asvs=asvs)


@main_bp.route('/<page_name>')
def other_page(page_name):
    return render_template('index.html', error_page=f'{page_name!r}')
