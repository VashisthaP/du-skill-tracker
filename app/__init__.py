"""
SkillHive - Flask Application Factory
=======================================
This module creates and configures the Flask application using the factory pattern.
The factory pattern allows creating multiple app instances (useful for testing)
and keeps the app creation logic centralized.
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

# ---------- Initialize Flask Extensions ----------
# These are created here (without app) and bound to the app in create_app()
# This pattern is called "Application Factories" in Flask documentation
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()
migrate = Migrate()
csrf = CSRFProtect()

# Configure login manager
login_manager.login_view = 'auth.login'  # Redirect to login page when @login_required fails
login_manager.login_message = 'Please sign in to access this page.'
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    """
    Application factory function.

    Args:
        config_name: Configuration to use ('development', 'production', 'testing').
                     Defaults to FLASK_ENV environment variable or 'development'.

    Returns:
        Flask application instance, fully configured and ready to run.
    """
    app = Flask(__name__)

    # ---------- Load Configuration ----------
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    from app.config import config_by_name
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # ---------- Initialize Extensions with App ----------
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # ---------- Setup Logging ----------
    _configure_logging(app)

    # ---------- Setup Application Insights (Production) ----------
    if app.config.get('APPINSIGHTS_INSTRUMENTATIONKEY') and not app.config.get('DEV_MODE'):
        _setup_application_insights(app)

    # ---------- Ensure Upload Directory Exists ----------
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)

    # ---------- Register Blueprints (Route Modules) ----------
    _register_blueprints(app)

    # ---------- Register Error Handlers ----------
    _register_error_handlers(app)

    # ---------- Register Template Context Processors ----------
    _register_context_processors(app)

    # ---------- Register Custom Template Filters ----------
    _register_template_filters(app)

    # ---------- Create Database Tables ----------
    with app.app_context():
        from app import models  # noqa: F401 - Import models so SQLAlchemy knows about them
        db.create_all()

        # Seed default skills if the skills table is empty
        _seed_default_skills(app)

    app.logger.info(f"SkillHive started in {config_name} mode")
    return app


def _configure_logging(app):
    """Configure application logging based on environment."""
    log_level = logging.DEBUG if app.config.get('DEBUG') else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    app.logger.setLevel(log_level)


def _setup_application_insights(app):
    """Setup Azure Application Insights for production monitoring.
    Uses logging-based integration (opencensus removed due to Flask 3.x incompatibility).
    """
    try:
        ikey = app.config.get('APPINSIGHTS_INSTRUMENTATIONKEY')
        if ikey:
            app.logger.info(f"Application Insights key configured ({ikey[:8]}...)")
            # For full telemetry, add azure-monitor-opentelemetry to requirements
            # and configure OpenTelemetry here.  Basic logging works out of the box
            # when APPINSIGHTS_INSTRUMENTATIONKEY is set as an App Service env var.
    except Exception as e:
        app.logger.warning(f"Failed to initialize Application Insights: {e}")


def _register_blueprints(app):
    """Register all Flask blueprints (route modules)."""
    from app.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.demands import demands_bp
    from app.routes.applications import applications_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)  # Root URL prefix
    app.register_blueprint(demands_bp, url_prefix='/demands')
    app.register_blueprint(applications_bp, url_prefix='/applications')
    app.register_blueprint(admin_bp, url_prefix='/admin')


def _register_error_handlers(app):
    """Register custom error pages for common HTTP errors."""
    from flask import render_template

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/404.html', message="Access denied. You don't have permission to view this page."), 403


def _register_template_filters(app):
    """Register custom Jinja2 template filters."""
    import markupsafe

    @app.template_filter('nl2br')
    def nl2br_filter(value):
        """Convert newlines to <br> tags for safe HTML display."""
        if not value:
            return ''
        escaped = markupsafe.escape(value)
        return markupsafe.Markup(str(escaped).replace('\n', '<br>\n'))


def _register_context_processors(app):
    """Register template context processors for global template variables."""

    @app.context_processor
    def inject_globals():
        """Make commonly used variables available in all templates."""
        return {
            'app_name': 'SkillHive',
            'app_version': '1.0.0',
            'current_year': 2026,
        }


def _seed_default_skills(app):
    """
    Seed the database with default skills if the skills table is empty.
    This runs on first startup to provide a base set of skills.
    """
    from app.models import Skill

    if Skill.query.count() == 0:
        default_skills = [
            # Programming Languages
            ('Python', 'Programming Language'),
            ('Java', 'Programming Language'),
            ('JavaScript', 'Programming Language'),
            ('TypeScript', 'Programming Language'),
            ('C#', 'Programming Language'),
            ('Go', 'Programming Language'),
            ('Rust', 'Programming Language'),
            ('SQL', 'Programming Language'),
            # Cloud & DevOps
            ('Azure', 'Cloud Platform'),
            ('AWS', 'Cloud Platform'),
            ('GCP', 'Cloud Platform'),
            ('Docker', 'DevOps'),
            ('Kubernetes', 'DevOps'),
            ('Terraform', 'DevOps'),
            ('CI/CD', 'DevOps'),
            ('Azure DevOps', 'DevOps'),
            # Frameworks
            ('React', 'Frontend Framework'),
            ('Angular', 'Frontend Framework'),
            ('Vue.js', 'Frontend Framework'),
            ('Node.js', 'Backend Framework'),
            ('.NET', 'Backend Framework'),
            ('Spring Boot', 'Backend Framework'),
            ('Flask', 'Backend Framework'),
            ('Django', 'Backend Framework'),
            # Data & AI
            ('Machine Learning', 'Data & AI'),
            ('Data Engineering', 'Data & AI'),
            ('Power BI', 'Data & AI'),
            ('Databricks', 'Data & AI'),
            ('Snowflake', 'Data & AI'),
            ('Gen AI', 'Data & AI'),
            ('NLP', 'Data & AI'),
            ('Computer Vision', 'Data & AI'),
            # Database
            ('PostgreSQL', 'Database'),
            ('MongoDB', 'Database'),
            ('Cosmos DB', 'Database'),
            ('Oracle', 'Database'),
            ('MySQL', 'Database'),
            # SAP & ERP
            ('SAP', 'Enterprise'),
            ('Salesforce', 'Enterprise'),
            ('ServiceNow', 'Enterprise'),
            # Testing & QA
            ('Selenium', 'Testing'),
            ('Automation Testing', 'Testing'),
            ('Performance Testing', 'Testing'),
            # Security
            ('Cybersecurity', 'Security'),
            ('IAM', 'Security'),
            # Other
            ('Agile/Scrum', 'Methodology'),
            ('Microservices', 'Architecture'),
            ('API Design', 'Architecture'),
        ]

        for skill_name, category in default_skills:
            skill = Skill(name=skill_name, category=category)
            db.session.add(skill)

        try:
            db.session.commit()
            app.logger.info(f"Seeded {len(default_skills)} default skills")
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Failed to seed skills: {e}")
