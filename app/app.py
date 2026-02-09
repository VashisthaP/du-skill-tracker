"""
SkillHive - Development Runner
================================
Entry point for running the app locally during development.
In production, wsgi.py is used with Gunicorn instead.

Usage (from project root):
    python -m flask run          (with FLASK_APP=wsgi:app)
    OR
    python wsgi.py
"""

import sys, os
# Ensure project root is on the path so 'from app import ...' resolves correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app

# Create the Flask app in development mode
app = create_app('development')

if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
