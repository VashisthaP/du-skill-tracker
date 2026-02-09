"""
SkillHive - Utility Decorators
================================
Role-based access control decorators for protecting routes.
Use these decorators on route functions to restrict access by user role.

Example:
    @demands_bp.route('/create')
    @login_required
    @pmo_required
    def create_demand():
        ...
"""

from functools import wraps
from flask import flash, redirect, url_for, abort
from flask_login import current_user


def role_required(*roles):
    """
    Generic decorator to restrict access to users with specific roles.

    Args:
        *roles: One or more role strings (e.g., 'admin', 'pmo', 'evaluator')

    Usage:
        @role_required('admin', 'pmo')
        def admin_only_view():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please sign in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """Restrict access to admin users only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Administrator access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def pmo_required(f):
    """Restrict access to PMO team and admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_pmo:
            flash('PMO team access required to perform this action.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def evaluator_required(f):
    """Restrict access to evaluators, PMO team, and admin users."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_evaluator:
            flash('Evaluator access required.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function
