#!/usr/bin/env python3

import json

import pandas as pd
import requests
from flask import Blueprint, current_app as app, flash, jsonify
from flask import make_response, redirect, render_template, request, url_for
from werkzeug.exceptions import HTTPException

from molmod.forms import (ApiResultForm, ApiSearchForm)
from molmod.main.main_routes import mpdebug


search_bp = Blueprint('search_bp', __name__,
                      template_folder='templates')


@search_bp.route('/search', methods=['GET', 'POST'])
def search():

    sform = ApiSearchForm()
    rform = ApiResultForm()

    # Get submitted dropdown options
    sform.gene.choices = [(x, x) for x in request.form.getlist('gene')]
    sform.fw_prim.choices = [(x, x) for x in request.form.getlist('fw_prim')]
    sform.rv_prim.choices = [(x, x) for x in request.form.getlist('rv_prim')]
    sform.kingdom.choices = [(x, x) for x in request.form.getlist('kingdom')]
    sform.phylum.choices = [(x, x) for x in request.form.getlist('phylum')]
    sform.classs.choices = [(x, x) for x in request.form.getlist('classs')]
    sform.oorder.choices = [(x, x) for x in request.form.getlist('oorder')]
    sform.family.choices = [(x, x) for x in request.form.getlist('family')]
    sform.genus.choices = [(x, x) for x in request.form.getlist('genus')]
    sform.species.choices = [(x, x) for x in request.form.getlist('species')]

    # If SEARCH was clicked
    if request.form.get('search_for_asv'):
        return render_template('search.html', sform=sform, rform=rform)

    return render_template('search.html', sform=sform)


@search_bp.route('/request_drop_options/<field>', methods=['GET', 'POST'])
def request_drop_options(field):
    sel = {}
    for f in ['gene', 'fw_prim', 'rv_prim', 'kingdom', 'phylum', 'classs', 'oorder', 'family', 'genus', 'species']:
        # Don't filter current dropdown
        if f == field:
            sel[f] = []
        else:
            sel[f] = get_selected(f)

    # For select2 search and pagination
    term = request.form['term']
    page = request.form['page']
    # See https://stackoverflow.com/questions/32533757/select2-v4-how-to-paginate-results-using-ajax for pagination

    url = "http://localhost:3000/rpc/tax_drop_options"
    payload = json.dumps({'field': field, 'term': term, 'gene': sel['gene'], 'fw_prim': sel['fw_prim'], 'rv_prim': sel['rv_prim'], 'kingdom': sel['kingdom'], 'phylum': sel['phylum'], 'classs': sel[
                         'classs'], 'oorder': sel['oorder'], 'family': sel['family'], 'genus': sel['genus'], 'species': sel['species']})
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        return response.text
    except:
        return {[]}


def get_selected(field: str):
    # Replace [''] with [] for zero-selection fields
    return [v for v in request.form[field].split(',') if v]


@search_bp.route('/search_run', methods=['POST'])
def search_run():

    # Set base URL for api search
    url = f"{app.config['API_URL']}/app_search_mixs_tax"

    # Get selected genes and/or primers
    gene_lst = request.form.getlist('gene')
    fw_lst = request.form.getlist('fw_prim')
    rv_lst = request.form.getlist('rv_prim')
    kingdom_lst = request.form.getlist('kingdom')
    phylum_lst = request.form.getlist('phylum')
    class_lst = request.form.getlist('classs')
    order_lst = request.form.getlist('oorder')
    family_lst = request.form.getlist('family')
    genus_lst = request.form.getlist('genus')
    species_lst = request.form.getlist('species')
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
        # msg = 'Sorry, search is disabled due to DB connection failure.'
        # # return "Error: " + str(e)
        # flash(msg, category='error')
        return None
    else:
        # Convert json to list of dicts
        return {"data": json.loads(response.text)}
