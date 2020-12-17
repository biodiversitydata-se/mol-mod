#!/usr/bin/env python3

import json

import requests
from flask import Blueprint
from flask import render_template, request
from werkzeug.exceptions import HTTPException

from molmod.forms import (ApiResultForm, ApiSearchForm)
from molmod.main.main_routes import mpdebug

from ..config import get_config
CONFIG = get_config()

search_bp = Blueprint('search_bp', __name__,
                      template_folder='templates')


@search_bp.route('/search', methods=['GET', 'POST'])
def search():

    sform = ApiSearchForm()
    rform = ApiResultForm()

    # Feed selected dropdown options back to client
    sform.gene.choices = [(x, x) for x in request.form.getlist('gene')]
    sform.sub.choices = [(x, x) for x in request.form.getlist('sub')]
    sform.fw_prim.choices = [(x, x) for x in request.form.getlist('fw_prim')]
    sform.rv_prim.choices = [(x, x) for x in request.form.getlist('rv_prim')]
    sform.kingdom.choices = [(x, x) for x in request.form.getlist('kingdom')]
    sform.phylum.choices = [(x, x) for x in request.form.getlist('phylum')]
    sform.classs.choices = [(x, x) for x in request.form.getlist('classs')]
    sform.oorder.choices = [(x, x) for x in request.form.getlist('oorder')]
    sform.family.choices = [(x, x) for x in request.form.getlist('family')]
    sform.genus.choices = [(x, x) for x in request.form.getlist('genus')]
    sform.species.choices = [(x, x) for x in request.form.getlist('species')]

    # Only include result form if SEARCH was clicked
    if request.form.get('search_for_asv'):
        return render_template('search.html', sform=sform, rform=rform)
    return render_template('search.html', sform=sform)


@search_bp.route('/request_drop_options/<field>', methods=['GET', 'POST'])
def request_drop_options(field):
    '''Forwards ajax request for filtered dropdown options to
    postgREST/postgres function, and returns paginated JSON result'''
    # Make dict of posted filters
    # (e.g. selected kingdom(s), received as 'kingdom[]')
    # but exclude current field, to allow multiple choice
    payload = {k.replace('[]', ''): request.form.getlist(k)
               for k, v in request.form.items() if k.replace('[]', '')
               not in ['term', 'page', field]}
    # Add (typed search) term, and field to be filtered, as str
    payload.update({'field': field, 'term': request.form['term']})
    # Add pagination
    limit = 25
    offset = (int(request.form['page']) - 1) * limit
    payload.update({'nlimit': limit, 'noffset': offset})
    url = f"{CONFIG.POSTGREST}/rpc/app_drop_options"
    payload = json.dumps(payload)
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.request("POST", url, headers=headers, data=payload)
    except Exception:
        return {[]}
    else:
        results = json.loads(response.text)[0]['data']['results']
        count = json.loads(response.text)[0]['data']['count']
        return {'results': results,
                'pagination': {'more': (offset + limit) < count}}


@search_bp.route('/search_run', methods=['POST'])
def search_run():
    # Set base URL for api search
    url = f"{CONFIG.POSTGREST}/app_search_mixs_tax"

    # Example on reducing lines of code using for loops
    # search_filters = ['gene', 'sub', 'fw_prim', 'rv_prim', 'kingdom', 'phylum', 'classs', 'oorder', 'family', 'genus',
    #                  'species']

    # selected_genes_and_primers = {}
    # for search_filter in search_filters:
    #    value = request.form.getlist(search_filter)
    #    if value:
    #        selected_genes_and_primers[search_filter] = ','.join(map(str, value))

    # if selected_genes_and_primers:
    #    url += '?'
    #    for search_filter, value in selected_genes_and_primers.items():
    #        url += f'&{search_filter}=in.({value})'

    # Get selected genes and/or primers
    gene_lst = request.form.getlist('gene')
    sub_lst = request.form.getlist('sub')
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
        gene = ','.join(map(str, gene_lst))
        url += f'?gene=in.({gene})'
        # Use 'AND' for additional criteria, if any
        op = '&'
    # SUBREGION
    if len(sub_lst) > 0:
        sub = ','.join(map(str, sub_lst))
        url += f'{op}sub=in.({sub})'
        op = '&'
    # FW PRIMER
    if len(fw_lst) > 0:
        fw_prim = ','.join(map(str, fw_lst))
        url += f'{op}fw_prim=in.({fw_prim})'
        op = '&'
    if len(rv_lst) > 0:
        rv_prim = ','.join(map(str, rv_lst))
        url += f'{op}rv_prim=in.({rv_prim})'
        op = '&'
    # KINGDOM
    if len(kingdom_lst) > 0:
        kingdom = ','.join(map(str, kingdom_lst))
        url += f'{op}kingdom=in.({kingdom})'
        op = '&'
    # PHYLUM
    if len(phylum_lst) > 0:
        phylum = ','.join(map(str, phylum_lst))
        url += f'{op}phylum=in.({phylum})'
        op = '&'
    # CLASS
    if len(class_lst) > 0:
        classs = ','.join(map(str, class_lst))
        url += f'{op}classs=in.({classs})'
        op = '&'
    # ORDER
    if len(order_lst) > 0:
        orders = ','.join(map(str, order_lst))
        url += f'{op}oorder=in.({orders})'
        op = '&'
    # FAMILY
    if len(family_lst) > 0:
        family = ','.join(map(str, family_lst))
        url += f'{op}family=in.({family})'
        op = '&'
    # GENUS
    if len(genus_lst) > 0:
        genus = ','.join(map(str, genus_lst))
        url += f'{op}genus=in.({genus})'
        op = '&'
    # SPECIES
    if len(species_lst) > 0:
        species = ','.join(map(str, species_lst))
        url += f'{op}species=in.({species})'

    mpdebug(url)

    # Make api request
    try:
        response = requests.get(url)
        response.raise_for_status()
    except (requests.ConnectionError, requests.exceptions.HTTPError):
        # msg = 'Sorry, search is disabled due to DB connection failure.'
        # # return "Error: " + str(e)
        # flash(msg, category='error')
        return None
    else:
        # Convert json to list of dicts
        return {"data": json.loads(response.text)}
