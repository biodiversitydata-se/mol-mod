#!/usr/bin/env python

from flask import Blueprint, request, make_response, render_template, Response, redirect, url_for
from datetime import datetime as dt

# Local lib
from ..models import db, ASV

# if ref to global app obj is needed
# from flask import current_app as app

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/asvs')
def show_asvs():
    asvs = ASV.query.all()
    return render_template('asvs.html',
                           asvs=asvs,
                           title="ASV list")
# def show_asvs():
#     return render_template('asvs.html')

@main_bp.route('/api')
def api_test():
    return Response('Redirect worked!')

@main_bp.route('/about')
def redir_test():
    return redirect(url_for('.api_test'))

# @main_bp.route('/list', methods=['GET'])
# def show_asvs():
#     asvs = ASV.query.all()
#     return render_template('asvs.html',
#                            asvs=asvs,
#                            title="ASV list")
