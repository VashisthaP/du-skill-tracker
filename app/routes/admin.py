"""
SkillHive - Admin Routes
=========================
Administrative panel for user management, system statistics,
and portal configuration. Only accessible by admin users.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import User, Demand, Application, Skill
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__, template_folder='templates')


# =====================================================
# ADMIN DASHBOARD
# =====================================================

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """
    Admin dashboard with comprehensive system statistics.
    Shows user counts, demand metrics, and application analytics.
    """
    # User statistics
    user_stats = {
        'total': User.query.count(),
        'admins': User.query.filter_by(role='admin').count(),
        'pmo': User.query.filter_by(role='pmo').count(),
        'evaluators': User.query.filter_by(role='evaluator').count(),
        'resources': User.query.filter_by(role='resource').count(),
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

    # Application statistics
    app_stats = {
        'total': Application.query.count(),
        'applied': Application.query.filter_by(status='applied').count(),
        'under_evaluation': Application.query.filter_by(status='under_evaluation').count(),
        'selected': Application.query.filter_by(status='selected').count(),
        'rejected': Application.query.filter_by(status='rejected').count(),
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

    return render_template(
        'admin/dashboard.html',
        user_stats=user_stats,
        demand_stats=demand_stats,
        app_stats=app_stats,
        top_skills=top_skills,
        recent_users=recent_users,
    )


# =====================================================
# USER MANAGEMENT
# =====================================================

@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """
    List all users with filtering and role management.
    Admins can change user roles from this page.
    """
    page = request.args.get('page', 1, type=int)

    query = User.query

    # Role filter
    role_filter = request.args.get('role', '')
    if role_filter:
        query = query.filter_by(role=role_filter)

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
        filters={'role': role_filter, 'search': search}
    )


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@admin_required
def update_user_role(user_id):
    """
    Update a user's role.
    Valid roles: admin, pmo, evaluator, resource
    """
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', '')

    valid_roles = ['admin', 'pmo', 'evaluator', 'resource']
    if new_role not in valid_roles:
        flash('Invalid role specified.', 'danger')
        return redirect(url_for('admin.users'))

    # Prevent removing the last admin
    if user.role == 'admin' and new_role != 'admin':
        admin_count = User.query.filter_by(role='admin').count()
        if admin_count <= 1:
            flash('Cannot remove the last admin. Assign another admin first.', 'danger')
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
