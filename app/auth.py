"""
SkillHive - Authentication Module
===================================
OTP-based authentication restricted to @accenture.com email addresses.
Only users approved by the admin (pratyush.vashistha@accenture.com) can log in.

Flow:
  1. User enters @accenture.com email on login page
  2. System checks if user exists and is approved
  3. 6-digit OTP sent to the email (valid for 10 minutes)
  4. User enters OTP to complete login
"""

import random
from datetime import datetime, timezone
from flask import (
    Blueprint, redirect, url_for, session, request,
    flash, current_app, render_template
)
from flask_login import login_user, logout_user, current_user, login_required
from app import db, csrf
from app.models import User

# Create the auth blueprint
auth_bp = Blueprint('auth', __name__, template_folder='templates')

# Super admin email - auto-approved, always admin
SUPER_ADMIN_EMAIL = 'pratyush.vashistha@accenture.com'


# =====================================================
# HELPER: Send OTP Email
# =====================================================
def _send_otp_email(user, otp_code):
    """
    Send OTP email using Flask-Mail.
    Falls back to logging the OTP if email sending fails (dev mode).
    """
    try:
        from flask_mail import Message
        from app import mail

        msg = Message(
            subject=f'SkillHive Login OTP: {otp_code}',
            recipients=[user.email],
            html=render_template('auth/otp_email.html',
                                 user=user, otp_code=otp_code),
        )
        mail.send(msg)
        current_app.logger.info(f"OTP email sent to {user.email}")
        return True
    except Exception as e:
        current_app.logger.warning(
            f"Failed to send OTP email to {user.email}: {e}. "
            f"OTP for dev/testing: {otp_code}"
        )
        return False


# =====================================================
# AUTH ROUTES
# =====================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Step 1: User enters @accenture.com email.
    Validates domain, checks approval, generates and sends OTP.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if not email:
            flash('Please enter your email address.', 'warning')
            return render_template('auth/login.html')

        # Validate @accenture.com domain
        if not email.endswith('@accenture.com'):
            flash('Only @accenture.com email addresses are allowed.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Your account is not registered. Please contact the administrator '
                  'to get approved.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Contact the administrator.', 'danger')
            return render_template('auth/login.html')

        if not user.is_approved:
            flash('Your account is pending admin approval. Please contact '
                  'pratyush.vashistha@accenture.com for access.', 'warning')
            return render_template('auth/login.html')

        # Generate OTP and send email
        otp_code = user.generate_otp()
        db.session.commit()

        email_sent = _send_otp_email(user, otp_code)

        # Store email in session for OTP verification step
        session['otp_email'] = email

        if email_sent:
            flash(f'A 6-digit OTP has been sent to {email}. It expires in 10 minutes.', 'info')
        else:
            # Emergency fallback: Show OTP on screen for super admin only
            if user.is_super_admin:
                flash(f'Email delivery failed. Emergency OTP for super admin: {otp_code}', 'warning')
            else:
                flash(f'OTP generated but email delivery failed. Please contact your administrator.', 'warning')

        return redirect(url_for('auth.verify_otp'))

    return render_template('auth/login.html')


@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """
    Step 2: User enters the 6-digit OTP received via email.
    Validates OTP, logs user in on success.
    """
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    email = session.get('otp_email')
    if not email:
        flash('Please enter your email first.', 'warning')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp_code = request.form.get('otp', '').strip()

        if not otp_code or len(otp_code) != 6:
            flash('Please enter the 6-digit OTP.', 'warning')
            return render_template('auth/verify_otp.html', email=email)

        user = User.query.filter_by(email=email).first()

        if not user:
            flash('User not found. Please try logging in again.', 'danger')
            session.pop('otp_email', None)
            return redirect(url_for('auth.login'))

        if user.verify_otp(otp_code):
            db.session.commit()
            login_user(user, remember=True)
            session.pop('otp_email', None)

            current_app.logger.info(f"User logged in via OTP: {email}")
            flash(f'Welcome, {user.display_name}!', 'success')

            next_page = request.args.get('next') or url_for('main.dashboard')
            return redirect(next_page)
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
            return render_template('auth/verify_otp.html', email=email)

    return render_template('auth/verify_otp.html', email=email)


@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP to the user's email."""
    email = session.get('otp_email')
    if not email:
        flash('Please enter your email first.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user or not user.is_approved or not user.is_active:
        flash('Unable to resend OTP. Please try logging in again.', 'danger')
        session.pop('otp_email', None)
        return redirect(url_for('auth.login'))

    otp_code = user.generate_otp()
    db.session.commit()

    email_sent = _send_otp_email(user, otp_code)
    if email_sent:
        flash(f'A new OTP has been sent to {email}.', 'info')
    else:
        flash('OTP generated but email delivery failed. Check with your administrator.', 'warning')

    return redirect(url_for('auth.verify_otp'))


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Log the user out of the application.
    Clears the Flask session and redirects to the login page.
    """
    user_name = current_user.display_name
    session.clear()
    logout_user()
    flash(f'Goodbye, {user_name}! You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
