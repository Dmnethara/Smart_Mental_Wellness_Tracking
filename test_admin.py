import pytest
from datetime import datetime, timedelta
from app import create_app
from models import db, User, WellnessLog

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"
    SERVER_NAME = "localhost"

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

@pytest.fixture
def seed_data(app):
    with app.app_context():
        # Register a student
        student1 = User(
            name="Alice Student",
            email="alice@susl.ac.lk",
            reg_number="REG001",
            role="student",
            password_hash="hashed_password"
        )
        # Register another student
        student2 = User(
            name="Bob Student",
            email="bob@susl.ac.lk",
            reg_number="REG002",
            role="student",
            password_hash="hashed_password"
        )
        # Register an admin
        admin = User(
            name="Admin User",
            email="admin@susl.ac.lk",
            reg_number="ADMIN01",
            role="admin",
            password_hash="hashed_password"
        )
        # Register a counselor
        counselor = User(
            name="Counselor User",
            email="counselor@susl.ac.lk",
            reg_number="COUNSELOR01",
            role="counselor",
            password_hash="hashed_password"
        )
        db.session.add_all([student1, student2, admin, counselor])
        db.session.commit()
        
        # Add some wellness logs for Alice (At-Risk: stress=5 for 5 consecutive days)
        today = datetime.now().date()
        for i in range(5):
            log = WellnessLog(
                user_id=student1.id,
                log_date=today - timedelta(days=i),
                mood_score=2,
                stress_level=5,
                sleep_hours=5.0,
                sleep_quality=2,
                academic_workload=4
            )
            db.session.add(log)
            
        # Add some healthy logs for Bob
        for i in range(3):
            log = WellnessLog(
                user_id=student2.id,
                log_date=today - timedelta(days=i),
                mood_score=4,
                stress_level=2,
                sleep_hours=8.0,
                sleep_quality=4,
                academic_workload=2
            )
            db.session.add(log)
            
        db.session.commit()
        
        return {
            'student1_id': student1.id,
            'student2_id': student2.id,
            'admin_id': admin.id,
            'counselor_id': counselor.id
        }


def register_and_login(client, name, email, reg, password, role='student', app=None):
    client.post('/register', data={
        'name': name,
        'email': email,
        'reg_number': reg,
        'password': password,
        'confirm_password': password
    })
    # If we need to set role to admin/counselor, we update the DB under app context
    if role != 'student' and app:
        with app.app_context():
            u = User.query.filter_by(email=email).first()
            if u:
                u.role = role
                db.session.commit()
                
    response = client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)
    return response

def test_admin_panel_access(client, app):
    """Verify students are blocked (403) and staff (admin/counselor) are allowed (200)."""
    # 1. Register and login student
    register_and_login(client, "Student", "student@susl.ac.lk", "REG001", "Password123", "student", app)
    
    # Try accessing admin views
    for route in ['/admin/dashboard', '/admin/students', '/admin/analytics', '/admin/alerts']:
        response = client.get(route)
        assert response.status_code == 403
        
    client.get('/logout')
    
    # 2. Register and login admin
    register_and_login(client, "Admin", "admin@susl.ac.lk", "ADMIN01", "Password123", "admin", app)
    for route in ['/admin/dashboard', '/admin/students', '/admin/analytics', '/admin/alerts']:
        response = client.get(route)
        assert response.status_code == 200
        
    client.get('/logout')
    
    # 3. Register and login counselor
    register_and_login(client, "Counselor", "counselor@susl.ac.lk", "COUNSELOR01", "Password123", "counselor", app)
    for route in ['/admin/dashboard', '/admin/students', '/admin/analytics', '/admin/alerts']:
        response = client.get(route)
        assert response.status_code == 200

def test_flag_student(client, app):
    """Verify counselors/admins can toggle the counseling flag on a student."""
    # Register student
    register_and_login(client, "Alice Student", "alice@susl.ac.lk", "REG001", "Password123", "student", app)
    client.get('/logout')
    
    # Register counselor
    register_and_login(client, "Counselor", "counselor@susl.ac.lk", "COUNSELOR01", "Password123", "counselor", app)
    
    # Find student ID
    with app.app_context():
        student = User.query.filter_by(email="alice@susl.ac.lk").first()
        student_id = student.id
        assert not student.is_flagged
        
    # Toggle flag (POST request)
    response = client.post(f'/admin/student/{student_id}/flag', follow_redirects=True)
    assert response.status_code == 200
    assert b"flagged for counseling" in response.data
    
    with app.app_context():
        student = User.query.get(student_id)
        assert student.is_flagged
        
    # Toggle flag again to remove
    response = client.post(f'/admin/student/{student_id}/flag', follow_redirects=True)
    assert response.status_code == 200
    assert b"unflagged" in response.data
    
    with app.app_context():
        student = User.query.get(student_id)
        assert not student.is_flagged

def test_pdf_export_security(client, app):
    """Test that PDF export checks authorization and prevents unauthorized downloads."""
    # 1. Register two students
    register_and_login(client, "Alice", "alice@susl.ac.lk", "REG001", "Password123", "student", app)
    with app.app_context():
        alice = User.query.filter_by(email="alice@susl.ac.lk").first()
        alice_id = alice.id
        # Seed a log for Alice so PDF has content
        log = WellnessLog(
            user_id=alice_id,
            log_date=datetime.now().date(),
            mood_score=4,
            stress_level=2,
            sleep_hours=8.0,
            sleep_quality=4,
            academic_workload=2
        )
        db.session.add(log)
        db.session.commit()
        
    client.get('/logout')
    
    register_and_login(client, "Bob", "bob@susl.ac.lk", "REG002", "Password123", "student", app)
    with app.app_context():
        bob = User.query.filter_by(email="bob@susl.ac.lk").first()
        bob_id = bob.id
        
    # Bob tries to download Alice's report -> expect 403
    response = client.get(f'/export/pdf?user_id={alice_id}')
    assert response.status_code == 403
    
    # Bob tries to download his own report -> expect 200 and PDF file
    response = client.get(f'/export/pdf?user_id={bob_id}')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
    assert f"wellness_REG002_".encode() in response.headers.get('Content-Disposition').encode()
    
    client.get('/logout')
    
    # 2. Counselor tries to download Alice's report -> expect 200
    register_and_login(client, "Counselor", "counselor@susl.ac.lk", "COUNSELOR01", "Password123", "counselor", app)
    response = client.get(f'/export/pdf?user_id={alice_id}')
    assert response.status_code == 200
    assert response.mimetype == 'application/pdf'
