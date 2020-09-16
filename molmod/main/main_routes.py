#!/usr/bin/env python3


from flask import Blueprint, flash
from flask import redirect, render_template


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


@main_bp.route('/<page_name>')
def other_page(page_name):
    msg = f'Sorry, page {page_name!r} does not exist.'
    flash(msg, category='error')
    return render_template('index.html')


def mpdebug(var, name=''):
    '''Prints var to console. Ex: mpdebug('gene', gene))'''
    print(f'\n\nDEBUG: Variable: {name}, Value: {var}, Type: {type(var)}', file=sys.stdout)
