#!/usr/bin/env python
'''Perhaps use later for db-admin'''

from flask import Blueprint, flash, make_response, render_template
from flask import redirect, url_for

import requests

from app.forms import LoginForm

admin_bp = Blueprint('admin_bp', __name__,
                     template_folder='templates')


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('main_bp.index'))
    return render_template('login.html', title='Sign In', form=form)
