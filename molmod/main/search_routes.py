#!/usr/bin/env python3

import json

import pandas as pd
import requests
from flask import Blueprint, current_app as app, flash, jsonify
from flask import make_response, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from molmod.forms import (ApiResultForm, ApiSearchForm)

search_bp = Blueprint('search_bp', __name__,
                          template_folder='templates')


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
        'primer': f'{base}/app_{dir}_primers?select=name,display',
        'gene':  f'{base}/app_genes',
        'kingdom': f'{base}/app_kingdoms',
        'phylum': f'{base}/app_phyla',
        'class': f'{base}/app_classes',
        'order': f'{base}/app_orders',
        'family': f'{base}/app_families',
        'genus': f'{base}/app_genera',
        'species': f'{base}/app_species'
    }
    return url.get(type, '')


@search_bp.route('/search', methods=['GET', 'POST'])
def search():

    sform = ApiSearchForm()
    rform = ApiResultForm()

    # Get dropdown options from api, and send to form
    sform.gene_sel.choices = request_drop_options('gene')
    sform.fw_prim_sel.choices = request_drop_options('primer', 'fw')
    sform.rv_prim_sel.choices = request_drop_options('primer', 'rv')
    sform.kingdom_sel.choices = request_drop_options('kingdom')
    sform.phylum_sel.choices = request_drop_options('phylum')
    sform.class_sel.choices = request_drop_options('class')
    sform.order_sel.choices = request_drop_options('order')
    sform.family_sel.choices = request_drop_options('family')
    sform.genus_sel.choices = request_drop_options('genus')
    sform.species_sel.choices = request_drop_options('species')

    # Fix later
    # If any dropdowns have no options - warn about connection error
    for l in [sform.gene_sel.choices, sform.fw_prim_sel.choices, sform.rv_prim_sel.choices]:
        if (len(l) == 0):
            # support = "<a href='mailto:sbdi-mol-data-support@scilifelab.se' subject='ASV DB connection failure in molecular module'>Support</a>"
            msg = f'Sorry, gene and/or primer options are unavailable due to DB connection failure.'
            flash(msg, category='error')
            break

    # If SEARCH was clicked
    if request.form.get('search_for_asv'):
        # Set base URL for api search
        url = f"{app.config['API_URL']}/app_search_mixs_tax"

        # Get selected genes and/or primers
        gene_lst = request.form.getlist('gene_sel')
        fw_lst = request.form.getlist('fw_prim_sel')
        rv_lst = request.form.getlist('rv_prim_sel')
        kingdom_lst = request.form.getlist('kingdom_sel')
        phylum_lst = request.form.getlist('phylum_sel')
        class_lst = request.form.getlist('class_sel')
        order_lst = request.form.getlist('order_sel')
        family_lst = request.form.getlist('family_sel')
        genus_lst = request.form.getlist('genus_sel')
        species_lst = request.form.getlist('species_sel')
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
        if len(rv_lst) > 0:
            rv = ','.join(map(str, rv_lst))
            url += f'{op}rv_name=in.({rv})'
            op = '&'
        # KINGDOM
        if len(kingdom_lst) > 0:
            kingdoms = ','.join(map(str, kingdom_lst))
            url += f'{op}kingdom=in.({kingdoms})'
            op = '&'
        # PHYLUM
        if len(phylum_lst) > 0:
            phyla = ','.join(map(str, phylum_lst))
            url += f'{op}phylum=in.({phyla})'
            op = '&'
        # CLASS
        if len(class_lst) > 0:
            classes = ','.join(map(str, class_lst))
            url += f'{op}class=in.({classes})'
            op = '&'
        # ORDER
        if len(order_lst) > 0:
            orders = ','.join(map(str, order_lst))
            url += f'{op}oorder=in.({orders})'
            op = '&'
        # FAMILY
        if len(family_lst) > 0:
            families = ','.join(map(str, family_lst))
            url += f'{op}family=in.({families})'
            op = '&'
        # GENUS
        if len(genus_lst) > 0:
            genera = ','.join(map(str, genus_lst))
            url += f'{op}genus=in.({genera})'
            op = '&'
        # SPECIES
        if len(species_lst) > 0:
            species = ','.join(map(str, species_lst))
            url += f'{op}specific_epithet=in.({species})'

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

            return render_template('search.html', sform=sform, rform=rform, api_results=rdict_lst)

    return render_template('search.html', sform=sform)
