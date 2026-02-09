#!/bin/bash
# =====================================================
# SkillHive - Azure App Service Startup Script
# =====================================================
# This script is executed by Azure App Service on container start.
# It initializes the database and starts the Gunicorn WSGI server.

echo "=== SkillHive Startup ==="
echo "Starting database initialization..."

# Run database migrations / create tables and seed default users
python -c "
from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()
with app.app_context():
    db.create_all()
    # Seed default admin/PMO if no users exist
    if User.query.count() == 0:
        default_pw = generate_password_hash('Welcome@2026')
        users = [
            User(email='admin@accenture.com', display_name='Admin User', role='admin', enterprise_id='admin.user', password_hash=default_pw),
            User(email='pmo@accenture.com', display_name='PMO Manager', role='pmo', enterprise_id='pmo.manager', password_hash=default_pw),
            User(email='evaluator@accenture.com', display_name='Tech Evaluator', role='evaluator', enterprise_id='tech.eval', password_hash=default_pw),
            User(email='resource1@accenture.com', display_name='Priya Sharma', role='resource', enterprise_id='priya.sharma', password_hash=default_pw),
            User(email='resource2@accenture.com', display_name='Rahul Kumar', role='resource', enterprise_id='rahul.kumar', password_hash=default_pw),
        ]
        db.session.add_all(users)
        db.session.commit()
        print(f'Seeded {len(users)} default users.')
    print('Database initialization complete.')
"

echo "Starting Gunicorn server..."

# Start Gunicorn with optimized settings for B1 App Service Plan:
# - 2 workers (B1 has 1 core, 1.75GB RAM; 2 workers is optimal)
# - 600s timeout for long-running requests (Excel exports, etc.)
# - Access log to stdout for Application Insights
gunicorn \
    --bind=0.0.0.0:8000 \
    --timeout=600 \
    --workers=2 \
    --threads=4 \
    --access-logfile='-' \
    --error-logfile='-' \
    --log-level=info \
    wsgi:app
