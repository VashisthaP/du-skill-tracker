"""
SkillHive - Database-Based Authentication
==========================================
Handles user authentication via email + password stored in the database.
No external identity provider required - users are pre-provisioned by admins.

Flow:
  User visits /login → Enters email + password → Validated against DB
  → Flask-Login session set → Redirect to dashboard
"""

from flask import (
    Blueprint, redirect, url_for, session, request,
    flash, current_app, render_template
)
from flask_login import login_user, logout_user, current_user, login_required
from app import db, csrf
from app.models import User

# Create the auth blueprint
auth_bp = Blueprint('auth', __name__, template_folder='templates')


# =====================================================
# AUTH ROUTES
# =====================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page with email + password authentication.
    GET: Render the login form
    POST: Validate credentials against the database
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact your administrator.', 'danger')
                return render_template('auth/login.html')

            login_user(user, remember=True)
            current_app.logger.info(f"User logged in: {email}")
            flash(f'Welcome, {user.display_name}!', 'success')

            next_page = request.args.get('next') or url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Log the user out of the application.
    Clears the Flask session and redirects to the landing page.
    """
    user_name = current_user.display_name
    logout_user()
    session.clear()
    flash(f'Goodbye, {user_name}! You have been logged out.', 'info')
    return redirect(url_for('main.index'))
