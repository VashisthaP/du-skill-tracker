"""
SkillHive - WSGI Entry Point
=============================
This is the entry point for production deployment with Gunicorn.
Azure App Service uses this file to start the application.

Usage:
    gunicorn --bind=0.0.0.0:8000 wsgi:app
"""

from app import create_app

# Create the Flask application using the app factory
app = create_app()
