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
from app.models import User, Skill, Demand, Application, Resource


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
                rrd='RRD-TEST-001',
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
            demand = Demand(project_name='P1', rrd='RRD-001', career_level='11', created_by=pmo.id)
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


class TestResourceModel:
    """Tests for the Resource model (bulk upload supply)."""

    def test_create_resource(self, app):
        with app.app_context():
            pmo = User(email='pmo@test.com', display_name='PMO', role='pmo')
            db.session.add(pmo)
            db.session.flush()
            demand = Demand(
                project_name='Test Project',
                rrd='RRD-RES-001',
                career_level='10',
                created_by=pmo.id
            )
            db.session.add(demand)
            db.session.flush()
            resource = Resource(
                demand_id=demand.id,
                name='Jane Doe',
                personnel_no='EMP001',
                primary_skill='Python',
                management_level='TL',
                home_location='Noida',
                lock_status='No Lock',
                availability_status='On bench',
                email='jane@test.com',
                contact_details='9876543210',
                uploaded_by=pmo.id,
            )
            db.session.add(resource)
            db.session.commit()
            assert resource.id is not None
            assert resource.evaluation_status == 'pending'
            assert resource.status_display == 'Pending'
            assert resource.status_color == 'secondary'
            assert demand.resource_count == 1

    def test_resource_evaluation(self, app):
        with app.app_context():
            pmo = User(email='pmo2@test.com', display_name='PMO2', role='pmo')
            evaluator = User(email='eval@test.com', display_name='Eval', role='evaluator')
            db.session.add_all([pmo, evaluator])
            db.session.flush()
            demand = Demand(
                project_name='Eval Project',
                rrd='RRD-EVAL-001',
                career_level='11',
                created_by=pmo.id
            )
            db.session.add(demand)
            db.session.flush()
            resource = Resource(
                demand_id=demand.id,
                name='John Smith',
                primary_skill='Java',
                uploaded_by=pmo.id,
            )
            db.session.add(resource)
            db.session.commit()

            # Evaluate the resource
            resource.evaluation_status = 'accepted'
            resource.evaluation_remarks = 'Strong candidate'
            resource.evaluated_by = evaluator.id
            db.session.commit()

            assert resource.evaluation_status == 'accepted'
            assert resource.status_display == 'Accepted'
            assert resource.status_color == 'success'
            assert resource.evaluator.display_name == 'Eval'

    def test_resource_cascade_delete(self, app):
        with app.app_context():
            pmo = User(email='pmo3@test.com', display_name='PMO3', role='pmo')
            db.session.add(pmo)
            db.session.flush()
            demand = Demand(
                project_name='Cascade Test',
                rrd='RRD-DEL-001',
                career_level='9',
                created_by=pmo.id
            )
            db.session.add(demand)
            db.session.flush()
            for i in range(3):
                db.session.add(Resource(
                    demand_id=demand.id,
                    name=f'Resource {i}',
                    uploaded_by=pmo.id,
                ))
            db.session.commit()
            assert demand.resource_count == 3

            # Deleting the demand should cascade-delete resources
            db.session.delete(demand)
            db.session.commit()
            assert Resource.query.count() == 0
