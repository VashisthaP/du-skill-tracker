"""
SkillHive - Azure AD / Entra ID Authentication
================================================
Handles user authentication via Microsoft identity platform (MSAL).
Supports two modes:
  1. Production: Full Azure AD SSO with MSAL ConfidentialClient
  2. Development: Mock login for local testing without Azure AD

Flow (Production):
  User clicks "Sign In" → Redirect to Microsoft Login → Callback with auth code
  → Exchange for tokens → Fetch user profile from Graph API → Create/update local user
  → Set Flask-Login session → Redirect to dashboard
"""

import uuid
import msal
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
# MSAL HELPER FUNCTIONS
# =====================================================

def _build_msal_app(cache=None):
    """
    Build a ConfidentialClientApplication for Azure AD authentication.
    This is the core MSAL object that handles token acquisition.
    """
    return msal.ConfidentialClientApplication(
        current_app.config['AZURE_AD_CLIENT_ID'],
        authority=current_app.config['AZURE_AD_AUTHORITY'],
        client_credential=current_app.config['AZURE_AD_CLIENT_SECRET'],
        token_cache=cache
    )


def _build_auth_url(state=None):
    """
    Build the Azure AD authorization URL that users are redirected to for login.
    The 'state' parameter prevents CSRF attacks on the OAuth callback.
    """
    return _build_msal_app().get_authorization_request_url(
        scopes=current_app.config['AZURE_AD_SCOPE'],
        state=state or str(uuid.uuid4()),
        redirect_uri=current_app.config['AZURE_AD_REDIRECT_URI']
    )


def _get_token_from_code(code):
    """
    Exchange the authorization code (received in callback) for access/refresh tokens.
    The access token can be used to call Microsoft Graph API.
    """
    app_instance = _build_msal_app()
    result = app_instance.acquire_token_by_authorization_code(
        code,
        scopes=current_app.config['AZURE_AD_SCOPE'],
        redirect_uri=current_app.config['AZURE_AD_REDIRECT_URI']
    )
    return result


# =====================================================
# AUTH ROUTES
# =====================================================

@auth_bp.route('/login')
def login():
    """
    Initiate the login process.
    - In DEV_MODE: Show a simple dev login form
    - In Production: Redirect to Microsoft Azure AD login page
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if current_app.config.get('DEV_MODE'):
        # Development mode: show local login form
        return render_template('auth/dev_login.html')

    # Production: Generate a state token for CSRF protection and redirect to Azure AD
    session['auth_state'] = str(uuid.uuid4())
    auth_url = _build_auth_url(state=session['auth_state'])
    return redirect(auth_url)


@auth_bp.route('/callback')
def callback():
    """
    Azure AD OAuth2 callback endpoint.
    After user authenticates with Microsoft, they are redirected here with an auth code.
    We exchange the code for tokens and fetch the user's profile from Graph API.
    """
    # Verify state parameter to prevent CSRF
    if request.args.get('state') != session.get('auth_state'):
        flash('Authentication failed: Invalid state parameter.', 'danger')
        return redirect(url_for('main.index'))

    # Check for errors from Azure AD
    if 'error' in request.args:
        error_desc = request.args.get('error_description', 'Unknown error')
        current_app.logger.error(f"Azure AD auth error: {error_desc}")
        flash(f'Authentication failed: {error_desc}', 'danger')
        return redirect(url_for('main.index'))

    # Exchange authorization code for tokens
    code = request.args.get('code')
    if not code:
        flash('Authentication failed: No authorization code received.', 'danger')
        return redirect(url_for('main.index'))

    try:
        token_result = _get_token_from_code(code)
    except Exception as e:
        current_app.logger.error(f"Token acquisition failed: {e}")
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('main.index'))

    if 'error' in token_result:
        current_app.logger.error(f"Token error: {token_result.get('error_description')}")
        flash('Authentication failed. Please try again.', 'danger')
        return redirect(url_for('main.index'))

    # Extract user info from the ID token claims
    user_info = token_result.get('id_token_claims', {})
    azure_ad_id = user_info.get('oid', '')  # Azure AD Object ID
    email = user_info.get('preferred_username', '') or user_info.get('email', '')
    display_name = user_info.get('name', email.split('@')[0])

    if not email:
        flash('Could not retrieve your email from Azure AD.', 'danger')
        return redirect(url_for('main.index'))

    # Create or update the user in our local database
    user = _create_or_update_user(azure_ad_id, email, display_name)

    # Log the user in using Flask-Login
    login_user(user, remember=True)
    session.pop('auth_state', None)  # Clean up state token

    current_app.logger.info(f"User logged in: {email}")
    flash(f'Welcome, {display_name}! 👋', 'success')

    # Redirect to the page they originally tried to access, or dashboard
    next_page = session.pop('next_url', None) or url_for('main.dashboard')
    return redirect(next_page)


@auth_bp.route('/dev-login', methods=['POST'])
@csrf.exempt
def dev_login():
    """
    Development mode login - creates a mock user session for local testing.
    Only available when DEV_MODE=true in configuration.
    THIS MUST NOT BE AVAILABLE IN PRODUCTION.
    """
    if not current_app.config.get('DEV_MODE'):
        flash('Development login is not available in production.', 'danger')
        return redirect(url_for('auth.login'))

    email = request.form.get('email', 'dev@accenture.com')
    display_name = request.form.get('display_name', 'Dev User')
    role = request.form.get('role', 'admin')  # Default to admin for dev testing

    # Create or update dev user
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(
            email=email,
            display_name=display_name,
            enterprise_id=email.split('@')[0],
            role=role,
            azure_ad_id=f'dev-{uuid.uuid4().hex[:8]}'
        )
        db.session.add(user)
    else:
        user.display_name = display_name
        user.role = role

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Dev login error: {e}")
        flash('Login failed. Please try again.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user, remember=True)
    flash(f'Welcome, {display_name}! (Dev Mode - Role: {role})', 'success')
    return redirect(url_for('main.dashboard'))


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Log the user out of the application.
    Clears the Flask session and optionally redirects to Azure AD logout.
    """
    user_name = current_user.display_name
    logout_user()
    session.clear()

    if current_app.config.get('DEV_MODE'):
        flash(f'Goodbye, {user_name}! You have been logged out.', 'info')
        return redirect(url_for('main.index'))

    # In production, also sign out from Azure AD
    # This ensures the user is fully signed out from SSO
    tenant_id = current_app.config.get('AZURE_AD_TENANT_ID')
    post_logout_redirect = url_for('main.index', _external=True)
    azure_logout_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
        f"?post_logout_redirect_uri={post_logout_redirect}"
    )
    return redirect(azure_logout_url)


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _create_or_update_user(azure_ad_id, email, display_name):
    """
    Create a new user or update an existing one after Azure AD login.
    First user to register gets 'admin' role, others default to 'resource'.
    """
    user = User.query.filter_by(email=email).first()

    if user:
        # Update existing user's Azure AD info
        user.azure_ad_id = azure_ad_id
        user.display_name = display_name
    else:
        # Check if this is the first user (gets admin role)
        is_first_user = User.query.count() == 0
        user = User(
            azure_ad_id=azure_ad_id,
            email=email,
            display_name=display_name,
            enterprise_id=email.split('@')[0] if '@' in email else email,
            role='admin' if is_first_user else 'resource'
        )
        db.session.add(user)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating/updating user: {e}")
        # Try to fetch existing user on conflict
        user = User.query.filter_by(email=email).first()

    return user
