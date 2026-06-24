import pytest
from datetime import datetime, timedelta
from app import create_app
from models import db, User, WellnessLog
from wellness import calculate_streak, check_high_stress_risk

@pytest.fixture
def app():
    # Create the app with test configurations
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for unit testing endpoints
        "SECRET_KEY": "test-secret-key"
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def logged_in_client(client):
    # Register and log in the test user dynamically to ensure proper password hashing
    client.post('/register', data={
        'name': 'Nethara',
        'reg_number': '23CDS0847',
        'email': 'nethara@susl.lk',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    client.post('/login', data={
        'email': 'nethara@susl.lk',
        'password': 'Password123'
    })
    return client

def test_wellness_score_calculation(app):
    """Test that the new wellness score formula is computed correctly by the model listener."""
    with app.app_context():
        # Seed user for this test specifically
        user = User(name='Nethara', reg_number='23CDS0847', email='nethara@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        
        # Test Case 1: All optimal values (mood=5, stress=1, sleep_q=5, sleep_h=8, workload=1)
        # Components: mood=100, stress=100, sleep_q=100, sleep_h=20, workload=100 -> Sum = 420 -> /5 = 84.0
        log1 = WellnessLog(
            user_id=user.id,
            log_date=datetime.now().date(),
            mood_score=5,
            stress_level=1,
            sleep_hours=8.0,
            sleep_quality=5,
            academic_workload=1
        )
        db.session.add(log1)
        db.session.commit()
        
        assert float(log1.wellness_score) == 84.0

        # Test Case 2: Standard/Mid values (mood=3, stress=3, sleep_q=3, sleep_h=6.0, workload=3)
        # Components:
        # mood: 3 * 20 = 60
        # stress: (6-3) * 20 = 60
        # sleep_q: 3 * 20 = 60
        # sleep_h: min(6.0/8.0, 1.0) * 20 = 15
        # workload: (6-3) * 20 = 60
        # Sum = 60 + 60 + 60 + 15 + 60 = 255 -> /5 = 51.0
        log2 = WellnessLog(
            user_id=user.id,
            log_date=datetime.now().date() - timedelta(days=1),
            mood_score=3,
            stress_level=3,
            sleep_hours=6.0,
            sleep_quality=3,
            academic_workload=3
        )
        db.session.add(log2)
        db.session.commit()
        
        assert float(log2.wellness_score) == 51.0

def test_log_entry_validation(logged_in_client, app):
    """Test server-side range, boundary, future date, and duplicate validations."""
    today = datetime.now().date().isoformat()
    future_date = (datetime.now().date() + timedelta(days=1)).isoformat()

    # 1. Test out-of-range scores (mood_score = 6)
    response = logged_in_client.post('/log', data={
        'log_date': today,
        'mood_score': 6,  # Invalid
        'stress_level': 3,
        'sleep_hours': 7.5,
        'sleep_quality': 3,
        'academic_workload': 3,
        'notes': ''
    }, follow_redirects=True)
    assert b"Wellness scores must be between 1 and 5" in response.data

    # 2. Test out-of-range sleep hours (sleep_hours = -1)
    response = logged_in_client.post('/log', data={
        'log_date': today,
        'mood_score': 3,
        'stress_level': 3,
        'sleep_hours': -1.0,  # Invalid
        'sleep_quality': 3,
        'academic_workload': 3,
        'notes': ''
    }, follow_redirects=True)
    assert b"Sleep hours must be between 0 and 16 hours" in response.data

    # 3. Test future date validation
    response = logged_in_client.post('/log', data={
        'log_date': future_date,  # Invalid
        'mood_score': 3,
        'stress_level': 3,
        'sleep_hours': 7.5,
        'sleep_quality': 3,
        'academic_workload': 3,
        'notes': ''
    }, follow_redirects=True)
    assert b"Cannot record wellness logs for future dates" in response.data

    # 4. Test successful entry
    response = logged_in_client.post('/log', data={
        'log_date': today,
        'mood_score': 4,
        'stress_level': 2,
        'sleep_hours': 8.0,
        'sleep_quality': 4,
        'academic_workload': 2,
        'notes': 'Feeling great!'
    }, follow_redirects=True)
    assert b"Wellness entry successfully recorded" in response.data

    # 5. Test duplicate date check
    response = logged_in_client.post('/log', data={
        'log_date': today,  # Duplicate
        'mood_score': 3,
        'stress_level': 3,
        'sleep_hours': 7.0,
        'sleep_quality': 3,
        'academic_workload': 3,
        'notes': ''
    }, follow_redirects=True)
    assert b"You have already recorded a wellness log for" in response.data

def test_log_ownership_edit_delete(client, app):
    """Test that users cannot edit or delete other users' logs."""
    # Register and login User A
    client.post('/register', data={'name': 'User A', 'reg_number': 'REGA', 'email': 'usera@susl.lk', 'password': 'Password123', 'confirm_password': 'Password123'})
    client.post('/login', data={'email': 'usera@susl.lk', 'password': 'Password123'})
    
    # Create log for User A
    client.post('/log', data={
        'log_date': datetime.now().date().isoformat(),
        'mood_score': 4,
        'stress_level': 2,
        'sleep_hours': 8.0,
        'sleep_quality': 4,
        'academic_workload': 2,
        'notes': 'User A log'
    })
    
    # Retrieve log id
    with app.app_context():
        log = WellnessLog.query.first()
        log_id = log.id
        
    client.get('/logout')

    # Register and login User B
    client.post('/register', data={'name': 'User B', 'reg_number': 'REGB', 'email': 'userb@susl.lk', 'password': 'Password123', 'confirm_password': 'Password123'})
    client.post('/login', data={'email': 'userb@susl.lk', 'password': 'Password123'})

    # Try to edit User A's log as User B -> should abort(403)
    response = client.get(f'/log/edit/{log_id}')
    assert response.status_code == 403

    response = client.post(f'/log/edit/{log_id}', data={
        'log_date': datetime.now().date().isoformat(),
        'mood_score': 3,
        'stress_level': 3,
        'sleep_hours': 6.0,
        'sleep_quality': 3,
        'academic_workload': 3,
        'notes': 'Hijacked'
    })
    assert response.status_code == 403

    # Try to delete User A's log as User B -> should abort(403)
    response = client.post(f'/log/delete/{log_id}')
    assert response.status_code == 403

def test_streak_algorithm(app):
    """Test the logging streak calculation handles gaps and duplicates correctly."""
    with app.app_context():
        # Seed user for streak test
        user = User(name='Nethara', reg_number='23CDS0847', email='nethara@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        today = datetime.now().date()
        
        # Scenario 1: Empty logs -> streak = 0
        assert calculate_streak(user.id) == 0
        
        # Scenario 2: Logged today -> streak = 1
        log_today = WellnessLog(user_id=user.id, log_date=today, mood_score=3, stress_level=3, 
                                sleep_hours=7.0, sleep_quality=3, academic_workload=3)
        db.session.add(log_today)
        db.session.commit()
        assert calculate_streak(user.id) == 1

        # Scenario 3: Logged today + yesterday -> streak = 2
        log_yest = WellnessLog(user_id=user.id, log_date=today - timedelta(days=1), mood_score=3, stress_level=3, 
                               sleep_hours=7.0, sleep_quality=3, academic_workload=3)
        db.session.add(log_yest)
        db.session.commit()
        assert calculate_streak(user.id) == 2

        # Scenario 4: Logged today, yesterday, and 2 days ago -> streak = 3
        log_2d = WellnessLog(user_id=user.id, log_date=today - timedelta(days=2), mood_score=3, stress_level=3, 
                             sleep_hours=7.0, sleep_quality=3, academic_workload=3)
        db.session.add(log_2d)
        db.session.commit()
        assert calculate_streak(user.id) == 3

        # Scenario 5: Logged today, yesterday, 2 days ago, and 4 days ago (Gap at 3 days ago) -> streak = 3
        log_4d = WellnessLog(user_id=user.id, log_date=today - timedelta(days=4), mood_score=3, stress_level=3, 
                             sleep_hours=7.0, sleep_quality=3, academic_workload=3)
        db.session.add(log_4d)
        db.session.commit()
        assert calculate_streak(user.id) == 3

def test_risk_engine_logic(app):
    """Test that the rule-based risk engine triggers only when stress >= 4 for 5 consecutive days."""
    with app.app_context():
        # Seed user for risk engine test
        user = User(name='Nethara', reg_number='23CDS0847', email='nethara@susl.lk', 
                    password_hash='hashed_password', role='student')
        db.session.add(user)
        db.session.commit()
        today = datetime.now().date()
        
        # Scenario 1: Less than 5 logs -> risk = False
        for i in range(4):
            log = WellnessLog(user_id=user.id, log_date=today - timedelta(days=i), mood_score=3, 
                              stress_level=5, sleep_hours=7.0, sleep_quality=3, academic_workload=3)
            db.session.add(log)
        db.session.commit()
        assert check_high_stress_risk(user.id) is False

        # Scenario 2: 5 consecutive days of stress = 3 (moderate) -> risk = False
        WellnessLog.query.filter_by(user_id=user.id).delete() # clear
        for i in range(5):
            log = WellnessLog(user_id=user.id, log_date=today - timedelta(days=i), mood_score=3, 
                              stress_level=3, sleep_hours=7.0, sleep_quality=3, academic_workload=3)
            db.session.add(log)
        db.session.commit()
        assert check_high_stress_risk(user.id) is False

        # Scenario 3: 5 consecutive days with stress = 4 (high) -> risk = True
        WellnessLog.query.filter_by(user_id=user.id).delete() # clear
        for i in range(5):
            log = WellnessLog(user_id=user.id, log_date=today - timedelta(days=i), mood_score=3, 
                              stress_level=4, sleep_hours=7.0, sleep_quality=3, academic_workload=3)
            db.session.add(log)
        db.session.commit()
        assert check_high_stress_risk(user.id) is True

        # Scenario 4: 5 logs with high stress, but there is a gap in dates (days 1, 2, 3, 5, 6) -> risk = False
        WellnessLog.query.filter_by(user_id=user.id).delete() # clear
        dates = [today, today - timedelta(days=1), today - timedelta(days=2), today - timedelta(days=4), today - timedelta(days=5)]
        for d in dates:
            log = WellnessLog(user_id=user.id, log_date=d, mood_score=3, 
                              stress_level=5, sleep_hours=7.0, sleep_quality=3, academic_workload=3)
            db.session.add(log)
        db.session.commit()
        assert check_high_stress_risk(user.id) is False
