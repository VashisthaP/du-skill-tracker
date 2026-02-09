"""
SkillHive - Authentication Module
===================================
Currently uses database-based email + password authentication.
Azure AD / Entra ID SSO logic is preserved as comments for future enablement.

To enable SSO:
  1. Uncomment AZURE_AD_* settings in config.py
  2. Uncomment msal in requirements.txt and pip install msal
  3. Uncomment the SSO routes and helpers below
  4. Add Entra ID parameters back to azuredeploy.json
  5. Create an App Registration in Azure AD with redirect URI:
     https://<app-name>.azurewebsites.net/auth/callback
"""

# import uuid  # TODO: Uncomment for SSO
# import msal  # TODO: Uncomment for SSO
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
# AZURE AD SSO HELPER FUNCTIONS (Commented for future use)
# =====================================================
# TODO: Uncomment the following 3 functions to enable Azure AD SSO
#
# def _build_msal_app(cache=None):
#     """Build a ConfidentialClientApplication for Azure AD authentication."""
#     return msal.ConfidentialClientApplication(
#         current_app.config['AZURE_AD_CLIENT_ID'],
#         authority=current_app.config['AZURE_AD_AUTHORITY'],
#         client_credential=current_app.config['AZURE_AD_CLIENT_SECRET'],
#         token_cache=cache
#     )
#
# def _build_auth_url(state=None):
#     """Build the Azure AD authorization URL for login redirect."""
#     return _build_msal_app().get_authorization_request_url(
#         scopes=current_app.config['AZURE_AD_SCOPE'],
#         state=state or str(uuid.uuid4()),
#         redirect_uri=current_app.config['AZURE_AD_REDIRECT_URI']
#     )
#
# def _get_token_from_code(code):
#     """Exchange the authorization code for access/refresh tokens."""
#     app_instance = _build_msal_app()
#     return app_instance.acquire_token_by_authorization_code(
#         code,
#         scopes=current_app.config['AZURE_AD_SCOPE'],
#         redirect_uri=current_app.config['AZURE_AD_REDIRECT_URI']
#     )


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

    # ----- SSO MODE (uncomment to enable, remove DB login block below) -----
    # session['auth_state'] = str(uuid.uuid4())
    # auth_url = _build_auth_url(state=session['auth_state'])
    # return redirect(auth_url)
    # -----------------------------------------------------------------------

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


# =====================================================
# AZURE AD SSO CALLBACK (Commented for future use)
# =====================================================
# TODO: Uncomment to enable Azure AD SSO callback
#
# @auth_bp.route('/callback')
# def callback():
#     """Azure AD OAuth2 callback endpoint."""
#     if request.args.get('state') != session.get('auth_state'):
#         flash('Authentication failed: Invalid state parameter.', 'danger')
#         return redirect(url_for('main.index'))
#
#     if 'error' in request.args:
#         error_desc = request.args.get('error_description', 'Unknown error')
#         current_app.logger.error(f"Azure AD auth error: {error_desc}")
#         flash(f'Authentication failed: {error_desc}', 'danger')
#         return redirect(url_for('main.index'))
#
#     code = request.args.get('code')
#     if not code:
#         flash('Authentication failed: No authorization code received.', 'danger')
#         return redirect(url_for('main.index'))
#
#     try:
#         token_result = _get_token_from_code(code)
#     except Exception as e:
#         current_app.logger.error(f"Token acquisition failed: {e}")
#         flash('Authentication failed. Please try again.', 'danger')
#         return redirect(url_for('main.index'))
#
#     if 'error' in token_result:
#         current_app.logger.error(f"Token error: {token_result.get('error_description')}")
#         flash('Authentication failed. Please try again.', 'danger')
#         return redirect(url_for('main.index'))
#
#     user_info = token_result.get('id_token_claims', {})
#     azure_ad_id = user_info.get('oid', '')
#     email = user_info.get('preferred_username', '') or user_info.get('email', '')
#     display_name = user_info.get('name', email.split('@')[0])
#
#     if not email:
#         flash('Could not retrieve your email from Azure AD.', 'danger')
#         return redirect(url_for('main.index'))
#
#     user = _create_or_update_sso_user(azure_ad_id, email, display_name)
#     login_user(user, remember=True)
#     session.pop('auth_state', None)
#     current_app.logger.info(f"User logged in via SSO: {email}")
#     flash(f'Welcome, {display_name}!', 'success')
#     next_page = session.pop('next_url', None) or url_for('main.dashboard')
#     return redirect(next_page)
#
#
# def _create_or_update_sso_user(azure_ad_id, email, display_name):
#     """Create a new user or update an existing one after Azure AD login."""
#     user = User.query.filter_by(email=email).first()
#     if user:
#         user.azure_ad_id = azure_ad_id
#         user.display_name = display_name
#     else:
#         is_first_user = User.query.count() == 0
#         user = User(
#             azure_ad_id=azure_ad_id,
#             email=email,
#             display_name=display_name,
#             enterprise_id=email.split('@')[0] if '@' in email else email,
#             role='admin' if is_first_user else 'resource'
#         )
#         db.session.add(user)
#     try:
#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         current_app.logger.error(f"Error creating/updating user: {e}")
#         user = User.query.filter_by(email=email).first()
#     return user


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
    return redirect(url_for('auth.login'))

    # ----- SSO LOGOUT (uncomment to enable Azure AD sign-out) -----
    # tenant_id = current_app.config.get('AZURE_AD_TENANT_ID')
    # post_logout_redirect = url_for('main.index', _external=True)
    # azure_logout_url = (
    #     f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
    #     f"?post_logout_redirect_uri={post_logout_redirect}"
    # )
    # return redirect(azure_logout_url)
