"""
SkillHive - Application Configuration
======================================
Centralized configuration management for all environments.
Supports local development (SQLite + mock auth) and production (PostgreSQL + Azure AD).
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration shared across all environments."""

    # ---------- Flask Core ----------
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable FSQLAlchemy event system (saves memory)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max upload size for resumes

    # ---------- Database ----------
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///skillhive.db'  # Default: SQLite for local development
    )

    # ---------- Email (Office 365 SMTP) ----------
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.office365.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'SkillHive <noreply@accenture.com>')

    # ---------- Azure Blob Storage (Resume uploads) ----------
    AZURE_STORAGE_CONNECTION_STRING = os.environ.get('AZURE_STORAGE_CONNECTION_STRING', '')
    AZURE_STORAGE_CONTAINER = os.environ.get('AZURE_STORAGE_CONTAINER', 'resumes')

    # ---------- File Upload Settings ----------
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pptx', 'docx'}

    # ---------- Application Insights ----------
    APPINSIGHTS_INSTRUMENTATIONKEY = os.environ.get('APPINSIGHTS_INSTRUMENTATIONKEY', '')

    # ---------- Development Mode ----------
    # When True: enables SQLite, local file storage
    DEV_MODE = os.environ.get('DEV_MODE', 'false').lower() == 'true'

    # ---------- Pagination ----------
    DEMANDS_PER_PAGE = 12
    APPLICATIONS_PER_PAGE = 20


class DevelopmentConfig(Config):
    """Development configuration with debug mode and SQLite."""
    DEBUG = True
    DEV_MODE = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///skillhive.db')


class ProductionConfig(Config):
    """Production configuration for Azure deployment."""
    DEBUG = False
    DEV_MODE = False
    # In production, DATABASE_URL must be set to PostgreSQL connection string
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Enforce HTTPS in production
    PREFERRED_URL_SCHEME = 'https'


class TestingConfig(Config):
    """Testing configuration with in-memory SQLite."""
    TESTING = True
    DEV_MODE = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing


# Configuration dictionary for easy lookup
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
