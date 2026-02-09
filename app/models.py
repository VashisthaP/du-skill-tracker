"""
SkillHive - Database Models
============================
SQLAlchemy ORM models representing the core data entities:
- User: Employees authenticated via Azure AD
- Skill: Technology/skill taxonomy for demand matching
- Demand: Project resource requirements posted by PMO team
- DemandSkill: Many-to-many relationship between Demand and Skill
- Application: Resource applications for open demands
- ApplicationHistory: Audit trail for application status changes
"""

from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


# =====================================================
# USER LOADER - Required by Flask-Login
# =====================================================
@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login callback to reload user from session.
    Called on every request for authenticated users.
    """
    return User.query.get(int(user_id))


# =====================================================
# ASSOCIATION TABLE: Demand <-> Skill (Many-to-Many)
# =====================================================
demand_skills = db.Table(
    'demand_skills',
    db.Column('demand_id', db.Integer, db.ForeignKey('demands.id', ondelete='CASCADE'), primary_key=True),
    db.Column('skill_id', db.Integer, db.ForeignKey('skills.id', ondelete='CASCADE'), primary_key=True)
)


# =====================================================
# USER MODEL
# =====================================================
class User(UserMixin, db.Model):
    """
    User model synced from Azure AD / Entra ID.
    Roles:
        - admin: Full system access, user management
        - pmo: Create/manage demands, manage applications
        - evaluator: Evaluate applications, update status
        - resource: View demands, apply for evaluation (default)
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # Azure AD Object ID - kept for future SSO integration
    azure_ad_id = db.Column(db.String(255), unique=True, nullable=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    # Password hash for local authentication
    password_hash = db.Column(db.String(256), nullable=True)
    # Accenture Enterprise ID (e.g., "john.doe")
    enterprise_id = db.Column(db.String(50), nullable=True)
    # Role determines access level throughout the application
    role = db.Column(db.String(20), nullable=False, default='resource')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    demands_created = db.relationship('Demand', backref='creator', lazy='dynamic',
                                       foreign_keys='Demand.created_by')
    applications = db.relationship('Application', backref='applicant', lazy='dynamic',
                                    foreign_keys='Application.user_id')

    def set_password(self, password):
        """Hash and store a password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'

    @property
    def is_admin(self):
        """Check if user has admin privileges."""
        return self.role == 'admin'

    @property
    def is_pmo(self):
        """Check if user has PMO (demand management) privileges."""
        return self.role in ('admin', 'pmo')

    @property
    def is_evaluator(self):
        """Check if user has evaluator privileges."""
        return self.role in ('admin', 'evaluator', 'pmo')

    @property
    def display_role(self):
        """Human-readable role name for UI display."""
        role_names = {
            'admin': 'Administrator',
            'pmo': 'PMO Team',
            'evaluator': 'Evaluator',
            'resource': 'Resource'
        }
        return role_names.get(self.role, 'Resource')


# =====================================================
# SKILL MODEL
# =====================================================
class Skill(db.Model):
    """
    Technology/skill taxonomy used for demand matching and the trending skill cloud.
    Skills are pre-defined and can be extended by admins.
    """
    __tablename__ = 'skills'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    # Category for grouping skills (e.g., "Programming Language", "Cloud Platform")
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Skill {self.name}>'

    @staticmethod
    def get_or_create(name, category=None):
        """
        Get an existing skill by name or create a new one.
        Useful when PMO enters a new skill not in the predefined list.
        """
        skill = Skill.query.filter(db.func.lower(Skill.name) == name.lower().strip()).first()
        if not skill:
            skill = Skill(name=name.strip(), category=category or 'Other')
            db.session.add(skill)
        return skill


# =====================================================
# DEMAND MODEL
# =====================================================
class Demand(db.Model):
    """
    A project resource demand raised by the PMO team.
    Contains project details, required skills, and evaluator information.
    Status workflow: Open → In Progress → Filled / Cancelled
    """
    __tablename__ = 'demands'

    id = db.Column(db.Integer, primary_key=True)

    # ---------- Project Information ----------
    project_name = db.Column(db.String(255), nullable=False)
    project_code = db.Column(db.String(50), nullable=True)
    du_name = db.Column(db.String(255), nullable=False)
    client_name = db.Column(db.String(255), nullable=True)

    # ---------- Requirement Details ----------
    # Career Level: Accenture career levels 8 (Sr. Manager) to 12 (Associate)
    career_level = db.Column(db.String(10), nullable=False)
    num_positions = db.Column(db.Integer, nullable=False, default=1)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)

    # ---------- Priority & Status ----------
    # Priority: critical, high, medium, low
    priority = db.Column(db.String(20), nullable=False, default='medium')
    # Status: open, in_progress, filled, cancelled
    status = db.Column(db.String(20), nullable=False, default='open', index=True)

    # ---------- Evaluator Information ----------
    evaluator_name = db.Column(db.String(255), nullable=True)
    evaluator_email = db.Column(db.String(255), nullable=True)
    evaluator_contact = db.Column(db.String(50), nullable=True)

    # ---------- Description ----------
    description = db.Column(db.Text, nullable=True)
    additional_notes = db.Column(db.Text, nullable=True)

    # ---------- Metadata ----------
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ---------- Relationships ----------
    # Many-to-many with Skills via association table
    skills = db.relationship('Skill', secondary=demand_skills, lazy='subquery',
                              backref=db.backref('demands', lazy='dynamic'))
    # One-to-many with Applications
    applications = db.relationship('Application', backref='demand', lazy='dynamic',
                                    cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Demand {self.project_name} [{self.status}]>'

    @property
    def skills_display(self):
        """Comma-separated skill names for display."""
        return ', '.join(skill.name for skill in self.skills)

    @property
    def career_level_display(self):
        """Human-readable career level label."""
        cl_labels = {
            '8': 'CL8 - Senior Manager',
            '9': 'CL9 - Manager',
            '10': 'CL10 - Team Lead',
            '11': 'CL11 - Senior Analyst',
            '12': 'CL12 - Analyst'
        }
        return cl_labels.get(self.career_level, f'CL{self.career_level}')

    @property
    def priority_color(self):
        """Bootstrap color class for priority badge."""
        colors = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'secondary'
        }
        return colors.get(self.priority, 'secondary')

    @property
    def status_color(self):
        """Bootstrap color class for status badge."""
        colors = {
            'open': 'success',
            'in_progress': 'primary',
            'filled': 'secondary',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

    @property
    def status_display(self):
        """Human-readable status label."""
        return self.status.replace('_', ' ').title()

    @property
    def application_count(self):
        """Number of applications received for this demand."""
        return self.applications.count()

    @property
    def is_open(self):
        """Check if demand is still accepting applications."""
        return self.status in ('open', 'in_progress')


# =====================================================
# APPLICATION MODEL
# =====================================================
class Application(db.Model):
    """
    A resource's application for an open demand.
    Status workflow: Applied → Under Evaluation → Selected / Rejected
    """
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)

    # ---------- References ----------
    demand_id = db.Column(db.Integer, db.ForeignKey('demands.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    # ---------- Applicant Information ----------
    applicant_name = db.Column(db.String(255), nullable=False)
    enterprise_id = db.Column(db.String(50), nullable=True)
    current_project = db.Column(db.String(255), nullable=True)
    years_of_experience = db.Column(db.Float, nullable=True)
    skills_text = db.Column(db.Text, nullable=True)  # Applicant's self-reported skills

    # ---------- Resume ----------
    resume_filename = db.Column(db.String(255), nullable=True)
    # URL to resume in Azure Blob Storage (or local path in dev mode)
    resume_blob_url = db.Column(db.String(500), nullable=True)

    # ---------- Status & Workflow ----------
    # Status: applied, under_evaluation, selected, rejected
    status = db.Column(db.String(30), nullable=False, default='applied', index=True)
    remarks = db.Column(db.Text, nullable=True)  # Evaluator/PMO remarks

    # ---------- Metadata ----------
    applied_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # ---------- Relationships ----------
    history = db.relationship('ApplicationHistory', backref='application', lazy='dynamic',
                               cascade='all, delete-orphan',
                               order_by='ApplicationHistory.changed_at.desc()')

    def __repr__(self):
        return f'<Application {self.applicant_name} -> {self.demand_id} [{self.status}]>'

    @property
    def status_display(self):
        """Human-readable status label."""
        return self.status.replace('_', ' ').title()

    @property
    def status_color(self):
        """Bootstrap color class for status badge."""
        colors = {
            'applied': 'info',
            'under_evaluation': 'warning',
            'selected': 'success',
            'rejected': 'danger'
        }
        return colors.get(self.status, 'secondary')

    @property
    def status_icon(self):
        """Bootstrap icon name for status."""
        icons = {
            'applied': 'bi-send-check',
            'under_evaluation': 'bi-hourglass-split',
            'selected': 'bi-check-circle-fill',
            'rejected': 'bi-x-circle-fill'
        }
        return icons.get(self.status, 'bi-question-circle')


# =====================================================
# APPLICATION HISTORY MODEL (Audit Trail)
# =====================================================
class ApplicationHistory(db.Model):
    """
    Audit trail for application status changes.
    Every status change is recorded with who made the change and when.
    """
    __tablename__ = 'application_history'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id', ondelete='CASCADE'),
                               nullable=False, index=True)
    old_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to the user who made the change
    changer = db.relationship('User', foreign_keys=[changed_by])

    def __repr__(self):
        return f'<History App#{self.application_id}: {self.old_status} → {self.new_status}>'
