"""
SkillHive – Seed Data Script
Creates sample users, skills, demands, and applications for testing.

Usage:
    python scripts/seed_data.py
"""
import os
import sys
from datetime import date, timedelta

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DEV_MODE', 'true')
os.environ.setdefault('FLASK_ENV', 'development')

from app import create_app, db
from app.models import User, Skill, Demand, Application


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        DEFAULT_PASSWORD = 'Welcome@2026'

        # ---- Users ----
        users_data = [
            {'email': 'admin@accenture.com',     'display_name': 'Admin User',      'role': 'admin',     'enterprise_id': 'admin.user'},
            {'email': 'pmo@accenture.com',        'display_name': 'PMO Manager',     'role': 'pmo',       'enterprise_id': 'pmo.manager'},
            {'email': 'evaluator@accenture.com',  'display_name': 'Tech Evaluator',  'role': 'evaluator', 'enterprise_id': 'tech.eval'},
            {'email': 'resource1@accenture.com',  'display_name': 'Priya Sharma',    'role': 'resource',  'enterprise_id': 'priya.sharma'},
            {'email': 'resource2@accenture.com',  'display_name': 'Rahul Kumar',     'role': 'resource',  'enterprise_id': 'rahul.kumar'},
        ]
        users = {}
        for u in users_data:
            existing = User.query.filter_by(email=u['email']).first()
            if not existing:
                user = User(**u)
                user.set_password(DEFAULT_PASSWORD)
                db.session.add(user)
                users[u['role'] if u['role'] != 'resource' else u['enterprise_id']] = user
            else:
                # Ensure existing users also get a password if they don't have one
                if not existing.password_hash:
                    existing.set_password(DEFAULT_PASSWORD)
                users[u['role'] if u['role'] != 'resource' else u['enterprise_id']] = existing
        db.session.flush()

        # ---- Extra Skills (in addition to the 46 auto-seeded ones) ----
        extra_skills = [
            ('GenAI', 'Data & AI'), ('LangChain', 'Data & AI'),
            ('Prompt Engineering', 'Data & AI'), ('RAG', 'Data & AI'),
        ]
        for name, cat in extra_skills:
            Skill.get_or_create(name, cat)
        db.session.flush()

        # ---- Sample Demands ----
        pmo = users.get('pmo')
        if pmo and Demand.query.count() == 0:
            demands_data = [
                {
                    'project_name': 'Cloud Migration – BFSI Client',
                    'project_code': 'PRJ-2024-001',
                    'du_name': 'Cloud & Infrastructure',
                    'client_name': 'HDFC Bank',
                    'career_level': '10',
                    'num_positions': 3,
                    'start_date': date.today() + timedelta(days=15),
                    'end_date': date.today() + timedelta(days=180),
                    'priority': 'critical',
                    'evaluator_name': 'Tech Evaluator',
                    'evaluator_email': 'evaluator@accenture.com',
                    'evaluator_contact': '+91 98765 43210',
                    'description': 'Need experienced cloud engineers for large-scale migration from on-prem to Azure. Must have strong Azure, Terraform, and containerization skills.',
                    'skills': ['Azure', 'Terraform', 'Docker', 'Kubernetes', 'Python'],
                },
                {
                    'project_name': 'GenAI Chatbot Platform',
                    'project_code': 'PRJ-2024-002',
                    'du_name': 'Applied Intelligence',
                    'client_name': 'Internal',
                    'career_level': '11',
                    'num_positions': 5,
                    'start_date': date.today() + timedelta(days=7),
                    'end_date': date.today() + timedelta(days=120),
                    'priority': 'high',
                    'evaluator_name': 'Tech Evaluator',
                    'evaluator_email': 'evaluator@accenture.com',
                    'description': 'Building an enterprise GenAI chatbot using LangChain and Azure OpenAI. Looking for Python developers with AI/ML experience.',
                    'skills': ['Python', 'GenAI', 'LangChain', 'Azure', 'React'],
                },
                {
                    'project_name': 'SAP S/4HANA Upgrade',
                    'project_code': 'PRJ-2024-003',
                    'du_name': 'Enterprise Solutions',
                    'client_name': 'Tata Motors',
                    'career_level': '9',
                    'num_positions': 2,
                    'start_date': date.today() + timedelta(days=30),
                    'priority': 'medium',
                    'evaluator_name': 'Tech Evaluator',
                    'evaluator_email': 'evaluator@accenture.com',
                    'description': 'S/4HANA upgrade project. Need consultants with SAP ABAP and Fiori experience.',
                    'skills': ['SAP', 'ABAP', 'SAP Fiori', 'SQL Server'],
                },
                {
                    'project_name': 'React Native Mobile App',
                    'project_code': 'PRJ-2024-004',
                    'du_name': 'Digital Engineering',
                    'client_name': 'Flipkart',
                    'career_level': '12',
                    'num_positions': 4,
                    'start_date': date.today() + timedelta(days=10),
                    'end_date': date.today() + timedelta(days=90),
                    'priority': 'high',
                    'evaluator_name': 'Tech Evaluator',
                    'evaluator_email': 'evaluator@accenture.com',
                    'description': 'Cross-platform mobile app development. Looking for developers with React Native and TypeScript skills.',
                    'skills': ['React', 'TypeScript', 'Node.js', 'REST APIs'],
                },
            ]
            for d_data in demands_data:
                skill_names = d_data.pop('skills')
                demand = Demand(created_by=pmo.id, **d_data)
                for sn in skill_names:
                    skill = Skill.get_or_create(sn)
                    demand.skills.append(skill)
                db.session.add(demand)

            db.session.flush()

            # ---- Sample Applications ----
            resource1 = users.get('priya.sharma')
            demand1 = Demand.query.first()
            if resource1 and demand1 and Application.query.count() == 0:
                app = Application(
                    demand_id=demand1.id,
                    user_id=resource1.id,
                    applicant_name='Priya Sharma',
                    enterprise_id='priya.sharma',
                    current_project='Internal Bench',
                    years_of_experience=5,
                    skills_text='Azure, Python, Terraform, Docker',
                    status='under_evaluation',
                    remarks='Strong Azure profile. Schedule technical round.',
                )
                db.session.add(app)

        db.session.commit()
        print('✅  Seed data created successfully!')
        print(f'   Users:    {User.query.count()}')
        print(f'   Skills:   {Skill.query.count()}')
        print(f'   Demands:  {Demand.query.count()}')
        print(f'   Applications: {Application.query.count()}')


if __name__ == '__main__':
    seed()
