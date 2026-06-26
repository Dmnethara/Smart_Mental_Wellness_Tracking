import pytest
from datetime import datetime
from app import create_app
from models import db, User, WellnessLog

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"

@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_register_and_login(client):
    """Register a new user and login, asserting successful redirect to dashboard."""
    # 1. Register
    response = client.post('/register', data={
        'name': 'Integration Student',
        'email': 'intstudent@susl.ac.lk',
        'reg_number': 'INTREG01',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    }, follow_redirects=True)
    
    assert b"Registration successful" in response.data
    
    # 2. Login
    response = client.post('/login', data={
        'email': 'intstudent@susl.ac.lk',
        'password': 'SecurePassword1'
    }, follow_redirects=True)
    
    assert b"Welcome back, Integration Student" in response.data
    assert b"Dashboard" in response.data

def test_log_entry_saves_to_db(client, app):
    """Log in as a test user, submit a new log entry via POST /log, and verify it is persisted in the database."""
    # 1. Register and Login
    client.post('/register', data={
        'name': 'Log Student',
        'email': 'logstudent@susl.ac.lk',
        'reg_number': 'LOGREG01',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    })
    client.post('/login', data={
        'email': 'logstudent@susl.ac.lk',
        'password': 'SecurePassword1'
    })
    
    # 2. POST log entry
    today = datetime.now().date()
    response = client.post('/log', data={
        'log_date': today.isoformat(),
        'mood_score': '4',
        'stress_level': '2',
        'sleep_hours': '7.5',
        'sleep_quality': '4',
        'academic_workload': '2',
        'notes': 'Integration test entry'
    }, follow_redirects=True)
    
    assert b"Wellness entry successfully recorded" in response.data
    
    # 3. Query the database to assert record exists
    with app.app_context():
        user = User.query.filter_by(email='logstudent@susl.ac.lk').first()
        assert user is not None
        log = WellnessLog.query.filter_by(user_id=user.id, log_date=today).first()
        assert log is not None
        assert log.mood_score == 4
        assert log.stress_level == 2
        assert float(log.sleep_hours) == 7.5
        assert log.notes == 'Integration test entry'

def test_admin_cannot_see_other_user_logs(client, app):
    """Assert that a regular student is blocked (403) from accessing the admin panel student registry."""
    # 1. Register and Login as a regular student
    client.post('/register', data={
        'name': 'Regular Student',
        'email': 'regstudent@susl.ac.lk',
        'reg_number': 'REGSTUD01',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    })
    client.post('/login', data={
        'email': 'regstudent@susl.ac.lk',
        'password': 'SecurePassword1'
    })
    
    # 2. Try to access the admin students registry view
    response = client.get('/admin/students')
    
    # Assert 403 Forbidden
    assert response.status_code == 403
