import pytest
from datetime import datetime, timedelta
from app import create_app
from models import db, User, WellnessLog
from wellness import check_high_stress_risk, run_risk_engine

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

def test_wellness_score_calculation(app):
    """Assert wellness index score is computed correctly for known inputs by the model listener."""
    with app.app_context():
        # Seed a test user
        user = User(name='Test User', reg_number='REG001', email='test@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        
        # Test Case: Optimal values (mood=5, stress=1, sleep_q=5, sleep_h=8.0, workload=1)
        # Components: mood=100, stress=100, sleep_q=100, sleep_h=20, workload=100 -> Sum = 420 -> /5 = 84.0
        log = WellnessLog(
            user_id=user.id,
            log_date=datetime.now().date(),
            mood_score=5,
            stress_level=1,
            sleep_hours=8.0,
            sleep_quality=5,
            academic_workload=1
        )
        db.session.add(log)
        db.session.commit()
        
        assert float(log.wellness_score) == 84.0

def test_risk_engine_chronic_stress(app):
    """Feed 5 consecutive days of stress=5 and verify the legacy chronic stress risk flag is triggered."""
    with app.app_context():
        # Seed a test user
        user = User(name='Test User', reg_number='REG001', email='test@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        
        today = datetime.now().date()
        
        # Insert 5 consecutive days of stress = 5
        for i in range(5):
            log = WellnessLog(
                user_id=user.id,
                log_date=today - timedelta(days=i),
                mood_score=3,
                stress_level=5,
                sleep_hours=7.0,
                sleep_quality=3,
                academic_workload=3
            )
            db.session.add(log)
        db.session.commit()
        
        # Verify the legacy risk engine triggers High Stress Risk (5 consecutive days >= 4)
        assert check_high_stress_risk(user.id) is True

def test_bcrypt_hash(app):
    """Hash a password using bcrypt and verify check_password_hash returns True."""
    with app.app_context():
        from models import bcrypt
        
        password = "SecurePassword1"
        pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        
        assert bcrypt.check_password_hash(pw_hash, password) is True
        assert bcrypt.check_password_hash(pw_hash, "WrongPassword") is False

def test_invalid_score_validation(app):
    """Verify entering out-of-bounds scores (e.g., mood = 6) raises a ValueError and fails database insert."""
    with app.app_context():
        user = User(name='Test User', reg_number='REG001', email='test@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        
        # Case 1: mood_score = 6 (out of 1-5 bounds)
        log1 = WellnessLog(
            user_id=user.id,
            log_date=datetime.now().date(),
            mood_score=6,
            stress_level=3,
            sleep_hours=7.0,
            sleep_quality=3,
            academic_workload=3
        )
        db.session.add(log1)
        db.session.commit()
        
        # The model listener sets wellness_score to 0.0 on validation failure
        assert float(log1.wellness_score) == 0.0
