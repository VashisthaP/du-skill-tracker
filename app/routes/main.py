"""
SkillHive - Main Routes
========================
Handles the landing page, dashboard, and API endpoints for
skill cloud data and dashboard statistics.
"""

from flask import Blueprint, render_template, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app import db
from app.models import Demand, Skill, Application, demand_skills, User

main_bp = Blueprint('main', __name__, template_folder='templates')


# =====================================================
# PUBLIC ROUTES
# =====================================================

@main_bp.route('/')
def index():
    """
    Landing page - publicly visible.
    Shows the SkillHive hero section, quick stats, and skill cloud preview.
    If user is already logged in, redirect to dashboard.
    """
    if current_user.is_authenticated:
        return render_template('dashboard.html', **_get_dashboard_data())

    # Get public stats for the landing page
    stats = {
        'open_demands': Demand.query.filter_by(status='open').count(),
        'total_positions': db.session.query(
            func.coalesce(func.sum(Demand.num_positions), 0)
        ).filter(Demand.status.in_(['open', 'in_progress'])).scalar(),
        'total_skills': Skill.query.count(),
        'filled_positions': Demand.query.filter_by(status='filled').count(),
    }

    # Get top 10 trending skills for the landing page cloud
    trending_skills = _get_trending_skills(limit=15)

    # Get latest open demands (preview)
    latest_demands = (
        Demand.query
        .filter(Demand.status.in_(['open', 'in_progress']))
        .order_by(
            # Order by priority: critical first, then high, medium, low
            case(
                (Demand.priority == 'critical', 1),
                (Demand.priority == 'high', 2),
                (Demand.priority == 'medium', 3),
                (Demand.priority == 'low', 4),
                else_=5
            ),
            Demand.created_at.desc()
        )
        .limit(6)
        .all()
    )

    return render_template(
        'index.html',
        stats=stats,
        trending_skills=trending_skills,
        latest_demands=latest_demands
    )


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    Main dashboard - requires authentication.
    Shows personalized view based on user role:
    - Resource: Open demands, my applications, skill cloud
    - PMO: Demand management, application stats, quick actions
    - Admin: Full stats, user management shortcuts
    """
    return render_template('dashboard.html', **_get_dashboard_data())


# =====================================================
# API ENDPOINTS (JSON)
# =====================================================

@main_bp.route('/api/skill-cloud')
def api_skill_cloud():
    """
    API endpoint returning skill demand data for the trending skill cloud.
    Returns JSON: [{name: "Python", count: 15, category: "Programming Language"}, ...]
    Used by the JavaScript skill cloud visualization on the frontend.
    """
    skills_data = _get_trending_skills(limit=30)
    return jsonify(skills_data)


@main_bp.route('/api/stats')
@login_required
def api_stats():
    """
    API endpoint returning dashboard statistics as JSON.
    Used for real-time dashboard updates and chart data.
    """
    # Demand status distribution
    status_counts = (
        db.session.query(Demand.status, func.count(Demand.id))
        .group_by(Demand.status)
        .all()
    )

    # Priority distribution (open demands only)
    priority_counts = (
        db.session.query(Demand.priority, func.count(Demand.id))
        .filter(Demand.status.in_(['open', 'in_progress']))
        .group_by(Demand.priority)
        .all()
    )

    # Career level distribution (open demands only)
    cl_counts = (
        db.session.query(Demand.career_level, func.count(Demand.id))
        .filter(Demand.status.in_(['open', 'in_progress']))
        .group_by(Demand.career_level)
        .all()
    )

    # Application status distribution
    app_status_counts = (
        db.session.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )

    # Monthly demand trend (last 6 months)
    monthly_demands = (
        db.session.query(
            func.strftime('%Y-%m', Demand.created_at).label('month'),
            func.count(Demand.id)
        )
        .group_by('month')
        .order_by('month')
        .limit(6)
        .all()
    )

    return jsonify({
        'status_distribution': dict(status_counts),
        'priority_distribution': dict(priority_counts),
        'career_level_distribution': dict(cl_counts),
        'application_status': dict(app_status_counts),
        'monthly_trend': [{'month': m, 'count': c} for m, c in monthly_demands],
    })


@main_bp.route('/api/skills/search')
def api_skills_search():
    """
    API endpoint for skill autocomplete in the demand creation form.
    Accepts ?q=searchterm and returns matching skills.
    """
    query = (request_args_get_safe('q') or '').strip()
    if len(query) < 1:
        return jsonify([])

    skills = (
        Skill.query
        .filter(Skill.name.ilike(f'%{query}%'))
        .order_by(Skill.name)
        .limit(20)
        .all()
    )

    return jsonify([{'id': s.id, 'name': s.name, 'category': s.category} for s in skills])


def request_args_get_safe(key):
    """Safely get a query parameter from the request."""
    from flask import request
    return request.args.get(key, '')


# =====================================================
# HELPER FUNCTIONS
# =====================================================

def _get_trending_skills(limit=15):
    """
    Get skills ranked by number of open demands requiring them.
    Returns a list of dicts with skill name, category, and demand count.
    """
    trending = (
        db.session.query(
            Skill.name,
            Skill.category,
            func.count(demand_skills.c.demand_id).label('demand_count')
        )
        .join(demand_skills, Skill.id == demand_skills.c.skill_id)
        .join(Demand, Demand.id == demand_skills.c.demand_id)
        .filter(Demand.status.in_(['open', 'in_progress']))
        .group_by(Skill.id, Skill.name, Skill.category)
        .order_by(func.count(demand_skills.c.demand_id).desc())
        .limit(limit)
        .all()
    )

    return [
        {'name': name, 'category': category or 'Other', 'count': count}
        for name, category, count in trending
    ]


def _get_dashboard_data():
    """
    Gather all data needed for the dashboard template.
    Returns a dict of template variables.
    """
    # Overall stats
    stats = {
        'open_demands': Demand.query.filter_by(status='open').count(),
        'in_progress_demands': Demand.query.filter_by(status='in_progress').count(),
        'filled_demands': Demand.query.filter_by(status='filled').count(),
        'total_positions': db.session.query(
            func.coalesce(func.sum(Demand.num_positions), 0)
        ).filter(Demand.status.in_(['open', 'in_progress'])).scalar(),
        'total_applications': Application.query.count(),
        'pending_applications': Application.query.filter_by(status='applied').count(),
        'total_users': User.query.count(),
    }

    # Trending skills for the cloud
    trending_skills = _get_trending_skills(limit=20)

    # Latest open demands
    latest_demands = (
        Demand.query
        .filter(Demand.status.in_(['open', 'in_progress']))
        .order_by(Demand.created_at.desc())
        .limit(8)
        .all()
    )

    # User-specific data
    my_applications = []
    my_demands = []
    if current_user.is_authenticated:
        my_applications = (
            Application.query
            .filter_by(user_id=current_user.id)
            .order_by(Application.applied_at.desc())
            .limit(5)
            .all()
        )
        if current_user.is_pmo:
            my_demands = (
                Demand.query
                .filter_by(created_by=current_user.id)
                .order_by(Demand.created_at.desc())
                .limit(5)
                .all()
            )

    return {
        'stats': stats,
        'trending_skills': trending_skills,
        'latest_demands': latest_demands,
        'my_applications': my_applications,
        'my_demands': my_demands,
    }
