"""
SkillHive - Demand Routes
==========================
CRUD operations for project demands.
PMO team members can create, edit, and manage demands.
All authenticated users can view and filter demands.
"""

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from sqlalchemy import case
from app import db
from app.models import Demand, Skill, Application
from app.forms import DemandForm
from app.utils.decorators import pmo_required
from app.services.email_service import send_demand_notification

demands_bp = Blueprint('demands', __name__, template_folder='templates')


# =====================================================
# LIST DEMANDS (All authenticated users)
# =====================================================

@demands_bp.route('/')
@login_required
def list_demands():
    """
    List all demands with filtering and pagination.
    Supports filters: status, priority, career_level, skill, search text.
    """
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('DEMANDS_PER_PAGE', 12)

    # Start with base query
    query = Demand.query

    # ---------- Apply Filters ----------

    # Status filter (default: show open and in_progress)
    status_filter = request.args.get('status', '')
    if status_filter:
        query = query.filter(Demand.status == status_filter)
    else:
        # By default, show active demands (open + in_progress)
        query = query.filter(Demand.status.in_(['open', 'in_progress']))

    # Priority filter
    priority_filter = request.args.get('priority', '')
    if priority_filter:
        query = query.filter(Demand.priority == priority_filter)

    # Career level filter
    cl_filter = request.args.get('career_level', '')
    if cl_filter:
        query = query.filter(Demand.career_level == cl_filter)

    # DU Name filter
    du_filter = request.args.get('rrd', '')
    if du_filter:
        query = query.filter(Demand.rrd.ilike(f'%{du_filter}%'))

    # Skill filter - demands that require a specific skill
    skill_filter = request.args.get('skill', '')
    if skill_filter:
        query = query.filter(
            Demand.skills.any(Skill.name.ilike(f'%{skill_filter}%'))
        )

    # Text search (project name, rrd, description)
    search = request.args.get('search', '').strip()
    if search:
        search_pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Demand.project_name.ilike(search_pattern),
                Demand.rrd.ilike(search_pattern),
                Demand.description.ilike(search_pattern),
            )
        )

    # ---------- Apply Sorting ----------
    sort_by = request.args.get('sort', 'priority')
    if sort_by == 'newest':
        query = query.order_by(Demand.created_at.desc())
    elif sort_by == 'oldest':
        query = query.order_by(Demand.created_at.asc())
    elif sort_by == 'priority':
        query = query.order_by(
            case(
                (Demand.priority == 'critical', 1),
                (Demand.priority == 'high', 2),
                (Demand.priority == 'medium', 3),
                (Demand.priority == 'low', 4),
                else_=5
            ),
            Demand.created_at.desc()
        )
    else:
        query = query.order_by(Demand.created_at.desc())

    # ---------- Paginate Results ----------
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # Get unique RRD values for the filter dropdown
    rrd_values = (
        db.session.query(Demand.rrd)
        .distinct()
        .order_by(Demand.rrd)
        .all()
    )

    # Get all skills for the filter dropdown
    all_skills = Skill.query.order_by(Skill.name).all()

    return render_template(
        'demands/list.html',
        demands=pagination.items,
        pagination=pagination,
        rrd_values=[d[0] for d in rrd_values],
        all_skills=all_skills,
        # Pass current filter values back to template for "sticky" filters
        filters={
            'status': status_filter,
            'priority': priority_filter,
            'career_level': cl_filter,
            'rrd': du_filter,
            'skill': skill_filter,
            'search': search,
            'sort': sort_by,
        }
    )


# =====================================================
# VIEW DEMAND DETAIL (All authenticated users)
# =====================================================

@demands_bp.route('/<int:demand_id>')
@login_required
def detail(demand_id):
    """
    View full details of a specific demand.
    Shows project info, required skills, evaluator details, and application stats.
    """
    demand = Demand.query.get_or_404(demand_id)

    # Get applications for this demand (visible to PMO/evaluator)
    applications = []
    if current_user.is_pmo or current_user.is_evaluator:
        applications = demand.applications.order_by(
            Application.applied_at.desc()
        ).all()

    return render_template(
        'demands/detail.html',
        demand=demand,
        applications=applications
    )


# =====================================================
# CREATE DEMAND (PMO only)
# =====================================================

@demands_bp.route('/create', methods=['GET', 'POST'])
@login_required
@pmo_required
def create():
    """
    Create a new project demand.
    Only accessible by PMO team members and admins.
    """
    form = DemandForm()

    # Get all skills for the tag input autocomplete
    all_skills = Skill.query.order_by(Skill.name).all()

    if form.validate_on_submit():
        # Server-side skills validation
        skills_str = form.skills.data or ''
        if not skills_str.strip():
            flash('At least one skill is required.', 'warning')
            return render_template('demands/form.html', form=form, all_skills=all_skills, is_edit=False)

        try:
            # Create the demand object
            demand = Demand(
                project_name=form.project_name.data,
                project_code=form.project_code.data,
                rrd=form.rrd.data,
                career_level=form.career_level.data,
                num_positions=form.num_positions.data,
                start_date=form.start_date.data,
                end_date=form.end_date.data,
                priority=form.priority.data,
                evaluator_name=form.evaluator_name.data,
                evaluator_email=form.evaluator_email.data,
                evaluator_contact=form.evaluator_contact.data,
                description=form.description.data,
                additional_notes=form.additional_notes.data,
                created_by=current_user.id,
                status='open'
            )

            # Process skills (comma-separated from the hidden field)
            skills_str = form.skills.data or ''
            for skill_name in skills_str.split(','):
                skill_name = skill_name.strip()
                if skill_name:
                    skill = Skill.get_or_create(skill_name)
                    demand.skills.append(skill)

            db.session.add(demand)
            db.session.commit()

            # Send email notification to the demand raiser (current user)
            try:
                send_demand_notification(demand, 'created')
            except Exception as e:
                current_app.logger.warning(f"Failed to send demand creation email: {e}")

            flash(f'Demand "{demand.project_name}" created successfully! 🎉', 'success')
            return redirect(url_for('demands.detail', demand_id=demand.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating demand: {e}")
            flash('Failed to create demand. Please try again.', 'danger')

    return render_template(
        'demands/form.html',
        form=form,
        all_skills=all_skills,
        is_edit=False
    )


# =====================================================
# EDIT DEMAND (PMO only)
# =====================================================

@demands_bp.route('/<int:demand_id>/edit', methods=['GET', 'POST'])
@login_required
@pmo_required
def edit(demand_id):
    """
    Edit an existing demand.
    Only accessible by PMO team members and admins.
    """
    demand = Demand.query.get_or_404(demand_id)
    form = DemandForm(obj=demand)

    # Get all skills for the tag input
    all_skills = Skill.query.order_by(Skill.name).all()

    if request.method == 'GET':
        # Pre-populate the skills hidden field with current skills
        form.skills.data = ','.join(s.name for s in demand.skills)

    if form.validate_on_submit():
        # Server-side skills validation
        skills_str = form.skills.data or ''
        if not skills_str.strip():
            flash('At least one skill is required.', 'warning')
            return render_template('demands/form.html', form=form, demand=demand, all_skills=all_skills, is_edit=True)

        try:
            # Update demand fields
            demand.project_name = form.project_name.data
            demand.project_code = form.project_code.data
            demand.rrd = form.rrd.data
            demand.du_name = form.du_name.data
            demand.client_name = form.client_name.data
            demand.manager_name = form.manager_name.data
            demand.career_level = form.career_level.data
            demand.num_positions = form.num_positions.data
            demand.start_date = form.start_date.data
            demand.end_date = form.end_date.data
            demand.priority = form.priority.data
            demand.evaluator_name = form.evaluator_name.data
            demand.evaluator_email = form.evaluator_email.data
            demand.evaluator_contact = form.evaluator_contact.data
            demand.description = form.description.data
            demand.additional_notes = form.additional_notes.data

            # Update skills: clear existing and add new ones
            demand.skills.clear()
            skills_str = form.skills.data or ''
            for skill_name in skills_str.split(','):
                skill_name = skill_name.strip()
                if skill_name:
                    skill = Skill.get_or_create(skill_name)
                    demand.skills.append(skill)

            db.session.commit()
            flash(f'Demand "{demand.project_name}" updated successfully! ✅', 'success')
            return redirect(url_for('demands.detail', demand_id=demand.id))

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating demand: {e}")
            flash('Failed to update demand. Please try again.', 'danger')

    return render_template(
        'demands/form.html',
        form=form,
        demand=demand,
        all_skills=all_skills,
        is_edit=True
    )


# =====================================================
# UPDATE DEMAND STATUS (PMO only)
# =====================================================

@demands_bp.route('/<int:demand_id>/status', methods=['POST'])
@login_required
@pmo_required
def update_status(demand_id):
    """
    Update the status of a demand.
    Valid transitions: open → in_progress → filled/cancelled
    """
    demand = Demand.query.get_or_404(demand_id)
    new_status = request.form.get('status', '')

    valid_statuses = ['open', 'in_progress', 'filled', 'cancelled']
    if new_status not in valid_statuses:
        flash('Invalid status value.', 'danger')
        return redirect(url_for('demands.detail', demand_id=demand_id))

    old_status = demand.status
    demand.status = new_status

    try:
        db.session.commit()
        flash(
            f'Demand status updated: {old_status.replace("_", " ").title()} → '
            f'{new_status.replace("_", " ").title()} ✅',
            'success'
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating demand status: {e}")
        flash('Failed to update status.', 'danger')

    return redirect(url_for('demands.detail', demand_id=demand_id))


# =====================================================
# EXPORT DEMANDS TO EXCEL
# =====================================================

@demands_bp.route('/export')
@login_required
@pmo_required
def export_excel():
    """
    Export all demands to an Excel file.
    Includes all fields, skills, and application counts.
    """
    from app.services.export_service import export_demands_to_excel

    try:
        return export_demands_to_excel()
    except Exception as e:
        current_app.logger.error(f"Error exporting demands: {e}")
        flash('Failed to export demands. Please try again.', 'danger')
        return redirect(url_for('demands.list_demands'))
