from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from ..extensions import db
from ..models.user import User
from .forms       import SignupForm, LoginForm

auth_bp = Blueprint('auth_bp', __name__, template_folder='templates')

@auth_bp.route('/signup', methods=['GET','POST'])
def signup():
    form = SignupForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.strip().lower()).first():
            flash('Email already exists', 'error')
        else:
            user = User(
                name=form.name.data.strip(),
                email=form.email.data.strip().lower())
            user.set_password(form.password.data)
            db.session.add(user); db.session.commit()
            login_user(user); return redirect(url_for('main_bp.home'))
    return render_template('public/signup.html', form=form)

@auth_bp.route('/login', methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.verify_password(form.password.data):
            login_user(user); return redirect(url_for('main_bp.home'))
        flash('Invalid credentials', 'error')
    return render_template('public/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user(); return redirect(url_for('auth_bp.login'))
