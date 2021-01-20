#!/usr/bin/env python3
from flask import Blueprint, abort
from flask import render_template

main_bp = Blueprint('main_bp', __name__,
                    template_folder='templates')


@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')


@main_bp.route('/about')
def about():
    # abort(301)
    return render_template('about.html')
