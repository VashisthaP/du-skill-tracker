"""
SkillHive - Admin Routes
=========================
Administrative panel for user management, system statistics,
and portal configuration. Only accessible by admin users.
Super admin: pratyush.vashistha@accenture.com — has full control
over all users, roles, approvals, and can add/delete users.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import User, Demand, Application, Skill, Resource
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, template_folder='templates')

# Super admin email constant
SUPER_ADMIN_EMAIL = 'pratyush.vashistha@accenture.com'


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """
    Admin dashboard with comprehensive system statistics.
    Shows user counts, demand metrics, and resource analytics.
    """
    # User statistics
    user_stats = {
        'total': User.query.count(),
        'admins': User.query.filter_by(role='admin').count(),
        'pmo': User.query.filter_by(role='pmo').count(),
        'evaluators': User.query.filter_by(role='evaluator').count(),
        'resources': User.query.filter_by(role='resource').count(),
        'pending_approval': User.query.filter_by(is_approved=False).count(),
    }

    # Demand statistics
    demand_stats = {
        'total': Demand.query.count(),
        'open': Demand.query.filter_by(status='open').count(),
        'in_progress': Demand.query.filter_by(status='in_progress').count(),
        'filled': Demand.query.filter_by(status='filled').count(),
        'cancelled': Demand.query.filter_by(status='cancelled').count(),
        'critical': Demand.query.filter(
            Demand.status.in_(['open', 'in_progress']),
            Demand.priority == 'critical'
        ).count(),
    }

    # Resource evaluation statistics
    resource_stats = {
        'total': Resource.query.count(),
        'pending': Resource.query.filter_by(evaluation_status='pending').count(),
        'accepted': Resource.query.filter_by(evaluation_status='accepted').count(),
        'rejected': Resource.query.filter_by(evaluation_status='rejected').count(),
    }

    # Top demanded skills
    top_skills = (
        db.session.query(
            Skill.name,
            func.count().label('demand_count')
        )
        .join(Skill.demands)
        .filter(Demand.status.in_(['open', 'in_progress']))
        .group_by(Skill.name)
        .order_by(func.count().desc())
        .limit(10)
        .all()
    )

    # Recent users
    recent_users = (
        User.query
        .order_by(User.created_at.desc())
        .limit(10)
        .all()
    )

    # Users pending approval
    pending_users = (
        User.query
        .filter_by(is_approved=False)
        .order_by(User.created_at.desc())
        .all()
    )

    return render_template(
        'admin/dashboard.html',
        user_stats=user_stats,
        demand_stats=demand_stats,
        resource_stats=resource_stats,
        top_skills=top_skills,
        recent_users=recent_users,
        pending_users=pending_users,
    )


# =====================================================
# USER MANAGEMENT
# =====================================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    List all users with filtering, role management, and approval status.
    Admin can change roles, approve, deactivate, and delete users.
    """
    page = request.args.get('page', 1, type=int)

    query = User.query

    # Role filter
    role_filter = request.args.get('role', '')
    if role_filter:
        query = query.filter_by(role=role_filter)

    # Approval filter
    approval_filter = request.args.get('approved', '')
    if approval_filter == 'yes':
        query = query.filter_by(is_approved=True)
    elif approval_filter == 'no':
        query = query.filter_by(is_approved=False)

    # Search
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                User.display_name.ilike(search_pattern),
                User.email.ilike(search_pattern),
                User.enterprise_id.ilike(search_pattern),
            )
        )

    users_paginated = (
        query.order_by(User.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )

    return render_template(
        'admin/users.html',
        users=users_paginated,
        filters={'role': role_filter, 'search': search, 'approved': approval_filter}
    )


@admin_bp.route('/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    """
    Add a new user (admin only).
    Only @accenture.com emails allowed. User is auto-approved when added by admin.
    """
    email = request.form.get('email', '').strip().lower()
    display_name = request.form.get('display_name', '').strip()
    role = request.form.get('role', 'resource')

    if not email or not display_name:
        flash('Email and display name are required.', 'danger')
        return redirect(url_for('admin.users'))

    # Validate email domain
    if not email.endswith('@accenture.com'):
        flash('Only @accenture.com email addresses are allowed.', 'danger')
        return redirect(url_for('admin.users'))

    # Check for duplicates
    existing = User.query.filter_by(email=email).first()
    if existing:
        flash(f'User with email {email} already exists.', 'warning')
        return redirect(url_for('admin.users'))

    # Validate role
    valid_roles = ['admin', 'pmo', 'evaluator', 'resource']
    if role not in valid_roles:
        role = 'resource'

    # Only super admin can create other admins
    if role == 'admin' and current_user.email.lower() != SUPER_ADMIN_EMAIL:
        flash('Only the super admin can create admin users.', 'danger')
        return redirect(url_for('admin.users'))

    user = User(
        email=email,
        display_name=display_name,
        enterprise_id=email.split('@')[0] if '@' in email else email,
        role=role,
        is_active=True,
        is_approved=True,  # Auto-approved when added by admin
    )
    db.session.add(user)

    try:
        db.session.commit()
        flash(f'User "{display_name}" ({email}) added as {role.upper()} ✅', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding user: {e}")
        flash('Failed to add user.', 'danger')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """
    Update a user's role.
    Valid roles: admin, pmo, evaluator, resource.
    Only super admin can assign admin role.
    """
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '')

    valid_roles = ['admin', 'pmo', 'evaluator', 'resource']
    if new_role not in valid_roles:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.users'))

    # Protect super admin - cannot change their role
    if user.email.lower() == SUPER_ADMIN_EMAIL and new_role != 'admin':
        flash('Cannot change the super admin\'s role.', 'danger')
        return redirect(url_for('admin.users'))

    # Only super admin can assign admin role
    if new_role == 'admin' and current_user.email.lower() != SUPER_ADMIN_EMAIL:
        flash('Only the super admin can assign the admin role.', 'danger')
        return redirect(url_for('admin.users'))

    # Prevent removing the last admin
    if user.role == 'admin' and new_role != 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot remove the last admin.', 'danger')
            return redirect(url_for('admin.users'))

    old_role = user.role
    user.role = new_role

    try:
        db.session.commit()
        flash(
            f'Role updated for {user.display_name}: '
            f'{old_role.upper()} → {new_role.upper()} ✅',
            'success'
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating user role: {e}")
        flash('Failed to update user role.', 'danger')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_user(user_id):
    """Approve a user so they can log in via OTP."""
    user = User.query.get_or_404(user_id)

    if user.is_approved:
        flash(f'{user.display_name} is already approved.', 'info')
        return redirect(url_for('admin.users'))

    user.is_approved = True
    try:
        db.session.commit()
        flash(f'{user.display_name} has been approved! They can now log in. ✅', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error approving user: {e}")
        flash('Failed to approve user.', 'danger')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/revoke', methods=['POST'])
@login_required
@admin_required
def revoke_user(user_id):
    """Revoke user approval (deactivate) — user can no longer log in."""
    user = User.query.get_or_404(user_id)

    # Cannot deactivate super admin
    if user.email.lower() == SUPER_ADMIN_EMAIL:
        flash('Cannot deactivate the super admin.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_approved = False
    user.is_active = False
    try:
        db.session.commit()
        flash(f'{user.display_name} has been deactivated. They can no longer log in.', 'warning')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error revoking user: {e}")
        flash('Failed to revoke user access.', 'danger')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/activate', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    """Reactivate a deactivated user."""
    user = User.query.get_or_404(user_id)
    user.is_active = True
    user.is_approved = True
    try:
        db.session.commit()
        flash(f'{user.display_name} has been reactivated. ✅', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error activating user: {e}")
        flash('Failed to activate user.', 'danger')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """
    Permanently delete a user.
    Only super admin can delete users. Cannot delete self.
    """
    # Only super admin can delete users
    if current_user.email.lower() != SUPER_ADMIN_EMAIL:
        flash('Only the super admin can delete users.', 'danger')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)

    # Cannot delete self
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.users'))

    # Cannot delete super admin
    if user.email.lower() == SUPER_ADMIN_EMAIL:
        flash('Cannot delete the super admin account.', 'danger')
        return redirect(url_for('admin.users'))

    user_name = user.display_name
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User "{user_name}" has been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting user: {e}")
        flash('Failed to delete user. They may have associated data.', 'danger')

    return redirect(url_for('admin.users'))


# =====================================================
# SKILL MANAGEMENT
# =====================================================

@admin_bp.route('/skills')
@login_required
@admin_required
def skills():
    """List and manage all skills in the system."""
    all_skills = (
        Skill.query
        .order_by(Skill.category, Skill.name)
        .all()
    )

    return render_template('admin/skills.html', skills=all_skills)


@admin_bp.route('/skills/add', methods=['POST'])
@login_required
@admin_required
def add_skill():
    """Add a new skill to the taxonomy."""
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'Other').strip()

    if not name:
        flash('Skill name is required.', 'danger')
        return redirect(url_for('admin.skills'))

    # Check for duplicates
    existing = Skill.query.filter(func.lower(Skill.name) == name.lower()).first()
    if existing:
        flash(f'Skill "{name}" already exists.', 'warning')
        return redirect(url_for('admin.skills'))

    skill = Skill(name=name, category=category)
    db.session.add(skill)

    try:
        db.session.commit()
        flash(f'Skill "{name}" added successfully! ✅', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding skill: {e}")
        flash('Failed to add skill.', 'danger')

    return redirect(url_for('admin.skills'))


@admin_bp.route('/skills/<int:skill_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_skill(skill_id):
    """Delete a skill from the taxonomy."""
    skill = Skill.query.get_or_404(skill_id)

    try:
        db.session.delete(skill)
        db.session.commit()
        flash(f'Skill "{skill.name}" deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting skill: {e}")
        flash('Failed to delete skill. It may be in use by existing demands.', 'danger')

    return redirect(url_for('admin.skills'))
