#!/usr/bin/env python3

import io
import json
import subprocess
import sys

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


def request_drop_options(type: str, dir: str = ''):
    '''Makes API request for dropdown list options used in API search'''
    # Get API URL
    url = get_drop_url(type, dir)
    # Make api request
    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
        # return "Error: " + str(e)
        options = []
    else:
        # Convert json to list of dicts
        rdict_lst = json.loads(response.text)
        # Get list of unique (set of) value-display tuples
        options = [(x['name'], x['display']) for x in rdict_lst]
    finally:
        return options


def get_drop_url(type: str, dir: str = ''):
    base = app.config['API_URL']
    url = {
        'primer': f'{base}/app_filter_{dir}_primers?select=name,display',
        'gene':  f'{base}/app_genes',
        'kingdom': f'{base}/app_kingdoms',
        'phylum': f'{base}/app_filter_phyla'

    }
    return url.get(type, '')


@main_bp.route('/search_api', methods=['GET', 'POST'])
def search_api():

    sform = ApiSearchForm()
    rform = ApiResultForm()

    # Get dropdown options from api, and send to form
    sform.gene_sel.choices = request_drop_options('gene')
    sform.fw_prim_sel.choices = request_drop_options('primer', 'fw')
    sform.rv_prim_sel.choices = request_drop_options('primer', 'rv')
    sform.kingdom_sel.choices = request_drop_options('kingdom')
    sform.phylum_sel.choices = request_drop_options('phylum')

    # If any dropdowns have no options - warn about connection error
    for l in [sform.gene_sel.choices, sform.fw_prim_sel.choices, sform.rv_prim_sel.choices]:
        if (len(l) == 0):
            # support = "<a href='mailto:sbdi-mol-data-support@scilifelab.se' subject='ASV DB connection failure in molecular module'>Support</a>"
            msg = f'Sorry, gene and/or primer options are unavailable due to DB connection failure.'
            flash(msg, category='error')
            break

    # If SEARCH was clicked
    if request.form.get('search_for_asv') and sform.validate_on_submit():
        # Set base URL for api search
        url = f"{app.config['API_URL']}/app_asv_mixs_tax"

        # Get selected genes and/or primers
        gene_lst = request.form.getlist('gene_sel')
        fw_lst = request.form.getlist('fw_prim_sel')
        rv_lst = request.form.getlist('rv_prim_sel')
        kingdom_lst = request.form.getlist('kingdom_sel')
        phylum_lst = request.form.getlist('phylum_sel')
        # Set logical operator for URL filtering
        op = '?'

        # Modify URL according to selections
        # GENE
        if len(gene_lst) > 0:
            genes = ','.join(map(str, gene_lst))
            url += f'?gene=in.({genes})'
            # Use 'AND' for additional criteria, if any
            op = '&'
        # FW PRIMER
        if len(fw_lst) > 0:
            fw = ','.join(map(str, fw_lst))
            url += f'{op}fw_name=in.({fw})'
            op = '&'
        # KINGDOM
        if len(kingdom_lst) > 0:
            kingdoms = ','.join(map(str, kingdom_lst))
            url += f'{op}kingdom=in.({kingdoms})'
            op = '&'
        if len(rv_lst) > 0:
            rv = ','.join(map(str, rv_lst))
            url += f'{op}rv_name=in.({rv})'
            op = '&'
        # PHYLUM
        if len(phylum_lst) > 0:
            phyla = ','.join(map(str, phylum_lst))
            url += f'{op}phylum=in.({phyla})'
            op = '&'

        # Make api request
        try:
            response = requests.get(url)
            response.raise_for_status()
        except (requests.ConnectionError, requests.exceptions.HTTPError) as e:
            msg = 'Sorry, search is disabled due to DB connection failure.'
            # return "Error: " + str(e)
            flash(msg, category='error')
        else:
            # Convert json to list of dicts
            rdict_lst = json.loads(response.text)

            return render_template('search_api.html', sform=sform, rform=rform, api_results=rdict_lst)

    return render_template('search_api.html', sform=sform)


# # Perhaps use for third option on start page
# @main_bp.route('/list_asvs', methods=['GET'])
# def list_asvs():
#     url = f"{app.config['API_URL']}/app_asvs_for_blastdb"
#     response = requests.get(url)
#     asvs = json.loads(response.text)
#     return render_template('list_asvs.html', asvs=asvs)


@main_bp.route('/<page_name>')
def other_page(page_name):
    msg = f'Sorry, page {page_name!r} does not exist.'
    flash(msg, category='error')
    return render_template('index.html')


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
                    print(tabulate(df, headers='keys', tablefmt='psql'), file=sys.stdout)
                    return df


def mpdebug(var, name=''):
    '''Prints var to console. Ex: mpdebug('gene', gene))'''
    print(f'\n\nDEBUG: Variable: {name}, Value: {var}, Type: {type(var)}', file=sys.stdout)
