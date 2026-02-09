"""
SkillHive – Test Suite
Basic tests for app creation, models, and routes.
"""
import os
import pytest

os.environ['DEV_MODE'] = 'true'
os.environ['FLASK_ENV'] = 'testing'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app, db
from app.models import User, Skill, Demand, Application


@pytest.fixture
def app():
    """Create a test app instance."""
    app = create_app()
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': 'localhost',
    })
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


class TestAppCreation:
    def test_app_exists(self, app):
        assert app is not None

    def test_app_is_testing(self, app):
        assert app.config['TESTING'] is True

    def test_landing_page(self, client):
        resp = client.get('/')
        assert resp.status_code == 200
        assert b'SkillHive' in resp.data


class TestModels:
    def test_create_user(self, app):
        with app.app_context():
            user = User(
                email='test@accenture.com',
                display_name='Test User',
                role='resource'
            )
            user.set_password('TestPass@123')
            db.session.add(user)
            db.session.commit()
            assert user.id is not None
            assert user.role == 'resource'
            assert user.check_password('TestPass@123') is True
            assert user.check_password('wrong') is False

    def test_create_skill(self, app):
        with app.app_context():
            skill = Skill.get_or_create('Python', 'Programming Language')
            db.session.commit()
            assert skill.id is not None
            # Duplicate should return same
            skill2 = Skill.get_or_create('python')
            assert skill.id == skill2.id

    def test_create_demand(self, app):
        with app.app_context():
            user = User(email='pmo@test.com', display_name='PMO', role='pmo')
            user.set_password('Test@123')
            db.session.add(user)
            db.session.flush()
            demand = Demand(
                project_name='Test Project',
                du_name='Test DU',
                career_level='10',
                priority='high',
                created_by=user.id
            )
            skill = Skill.get_or_create('Python')
            demand.skills.append(skill)
            db.session.add(demand)
            db.session.commit()
            assert demand.id is not None
            assert demand.skills[0].name == 'Python'
            assert demand.status == 'open'

    def test_create_application(self, app):
        with app.app_context():
            user = User(email='res@test.com', display_name='Resource', role='resource')
            pmo = User(email='pmo2@test.com', display_name='PMO', role='pmo')
            db.session.add_all([user, pmo])
            db.session.flush()
            demand = Demand(project_name='P1', du_name='DU1', career_level='11', created_by=pmo.id)
            db.session.add(demand)
            db.session.flush()
            application = Application(
                demand_id=demand.id,
                user_id=user.id,
                applicant_name='Resource User',
                enterprise_id='res.user',
                years_of_experience=3
            )
            db.session.add(application)
            db.session.commit()
            assert application.status == 'applied'
            assert application.demand.project_name == 'P1'

    def test_user_roles(self, app):
        with app.app_context():
            admin = User(email='a@t.com', display_name='A', role='admin')
            pmo = User(email='p@t.com', display_name='P', role='pmo')
            evaluator = User(email='e@t.com', display_name='E', role='evaluator')
            db.session.add_all([admin, pmo, evaluator])
            db.session.commit()
            assert admin.is_admin is True
            assert pmo.is_pmo is True
            assert evaluator.is_evaluator is True


class TestRoutes:
    def test_demands_redirect_without_auth(self, client):
        resp = client.get('/demands/')
        assert resp.status_code in (200, 302)

    def test_api_skill_cloud(self, client):
        resp = client.get('/api/skill-cloud')
        assert resp.status_code == 200

    def test_api_stats(self, client):
        resp = client.get('/api/stats')
        assert resp.status_code in (200, 302)  # 302 if login required

    def test_404(self, client):
        resp = client.get('/nonexistent-page-xyz')
        assert resp.status_code == 404

    def test_login_page(self, client):
        resp = client.get('/auth/login')
        assert resp.status_code == 200
        assert b'Sign In' in resp.data

    def test_login_invalid_creds(self, client):
        resp = client.post('/auth/login', data={'email': 'bad@test.com', 'password': 'wrong'})
        assert resp.status_code == 200
        assert b'Invalid email or password' in resp.data
