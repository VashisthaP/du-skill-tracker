#!/bin/bash
# =====================================================
# SkillHive - Azure App Service Startup Script
# =====================================================
# This script is executed by Azure App Service on container start.
# It initializes the database and starts the Gunicorn WSGI server.

echo "=== SkillHive Startup ==="
echo "Starting database initialization..."

# Run database migrations / create tables
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Database tables created successfully.')"

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
