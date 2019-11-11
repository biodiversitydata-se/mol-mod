#!/usr/bin/env python
from flask import Blueprint, request, make_response, render_template, Response, redirect, url_for
from datetime import datetime as dt

# Local lib
from ..models import db, User
from ..forms import ContactForm

admin_bp = Blueprint('admin_bp', __name__,
                    template_folder='templates')

@admin_bp.route('/users', methods=['GET'])
def show_users():
    users = User.query.all()
    return render_template('users.html',
                           users=users,
                           title="Show Users")

@admin_bp.route('/create_user', methods=['GET'])
def create_user():
    # Test
    # username = None
    # email = None
    username = 'Ingvar'
    email = 'ingvar@gmail.com'
    # username = request.args.get('user')
    # email = request.args.get('email')
    if username and email:
        existing_user = User.query.filter(User.username == username or User.email == email).first()
        if existing_user:
            return make_response(f'{username} ({email}) already created!')
        new_user = User(username=username,
            email=email,
            created=dt.now(),
            bio="In West Philadelphia born and raised, on the playground is where I spent most of my days",
            admin=False)  # Create an instance of the User class
        db.session.add(new_user)  # Adds new User record to database
        db.session.commit()  # Commits all changes
        return make_response(f'{username} ({email}) successfully created!')
    return make_response("No user created!")

# FUNKAR EJ
@admin_bp.route('/contact', methods=('GET', 'POST'))
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        return redirect(url_for('.success'))
    return render_template('contact.html', form=form)

@admin_bp.route('/success')
def success():
    return Response('Thanks for your message!')
