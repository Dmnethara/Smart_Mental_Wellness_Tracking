import pytest
from app import create_app
from models import db, User

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

def test_home_page(client):
    """Test that the home page loads successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"System Online" in response.data

def test_registration_validation(client):
    """Test that registration validates fields, matching passwords, and password strength."""
    # Test missing fields
    response = client.post('/register', data={
        'name': 'Test Student',
        'reg_number': '',  # Empty
        'email': 'test@student.lk',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b"All fields are required" in response.data

    # Test mismatched passwords
    response = client.post('/register', data={
        'name': 'Test Student',
        'reg_number': '23CDS0847',
        'email': 'test@student.lk',
        'password': 'Password123',
        'confirm_password': 'DifferentPassword123'
    }, follow_redirects=True)
    assert b"Passwords do not match" in response.data

    # Test weak password (no number)
    response = client.post('/register', data={
        'name': 'Test Student',
        'reg_number': '23CDS0847',
        'email': 'test@student.lk',
        'password': 'PasswordNoNumber',
        'confirm_password': 'PasswordNoNumber'
    }, follow_redirects=True)
    assert b"Password must be at least 8 characters long and contain at least 1 number" in response.data

    # Test weak password (too short)
    response = client.post('/register', data={
        'name': 'Test Student',
        'reg_number': '23CDS0847',
        'email': 'test@student.lk',
        'password': 'Short1',
        'confirm_password': 'Short1'
    }, follow_redirects=True)
    assert b"Password must be at least 8 characters long and contain at least 1 number" in response.data

def test_registration_success(client, app):
    """Test that valid registration succeeds, hashes password, and defaults role to student."""
    response = client.post('/register', data={
        'name': 'Nethara Vidmanthi',
        'reg_number': '23CDS0847',
        'email': 'nethara@susl.lk',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    }, follow_redirects=True)
    
    assert b"Registration successful. Please login" in response.data
    
    # Verify user was saved and password is encrypted
    with app.app_context():
        user = User.query.filter_by(email='nethara@susl.lk').first()
        assert user is not None
        assert user.name == 'Nethara Vidmanthi'
        assert user.reg_number == '23CDS0847'
        assert user.role == 'student'
        assert user.password_hash != 'SecurePassword1'  # Should be hashed
        assert len(user.password_hash) > 20

def test_registration_duplicate(client):
    """Test that duplicate email or registration number is rejected."""
    # Register first user
    client.post('/register', data={
        'name': 'User One',
        'reg_number': 'REG001',
        'email': 'user1@susl.lk',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })

    # Try duplicate email
    response = client.post('/register', data={
        'name': 'User Two',
        'reg_number': 'REG002',
        'email': 'user1@susl.lk',  # Duplicate email
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b"An account with this email already exists" in response.data

    # Try duplicate registration number
    response = client.post('/register', data={
        'name': 'User Three',
        'reg_number': 'REG001',  # Duplicate reg number
        'email': 'user3@susl.lk',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)
    assert b"An account with this registration number already exists" in response.data

def test_login_flow(client):
    """Test login with valid and invalid credentials."""
    # Register a user
    client.post('/register', data={
        'name': 'Nethara',
        'reg_number': '23CDS0847',
        'email': 'nethara@susl.lk',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    })

    # Test login with incorrect password
    response = client.post('/login', data={
        'email': 'nethara@susl.lk',
        'password': 'WrongPassword1'
    }, follow_redirects=True)
    assert b"Invalid email or password" in response.data

    # Test login with non-existent email
    response = client.post('/login', data={
        'email': 'nonexistent@susl.lk',
        'password': 'SecurePassword1'
    }, follow_redirects=True)
    assert b"Invalid email or password" in response.data

    # Test login with valid credentials
    response = client.post('/login', data={
        'email': 'nethara@susl.lk',
        'password': 'SecurePassword1'
    }, follow_redirects=True)
    assert b"Welcome back, Nethara" in response.data
    assert b"Hello, <strong>Nethara</strong>" in response.data
    assert b"Student" in response.data  # Role badge shown in navbar

def test_logout(client):
    """Test logging out clears the session."""
    # Register and login
    client.post('/register', data={
        'name': 'Nethara',
        'reg_number': '23CDS0847',
        'email': 'nethara@susl.lk',
        'password': 'SecurePassword1',
        'confirm_password': 'SecurePassword1'
    })
    client.post('/login', data={
        'email': 'nethara@susl.lk',
        'password': 'SecurePassword1'
    })
    
    # Logout
    response = client.get('/logout', follow_redirects=True)
    assert b"You have been logged out successfully" in response.data
    assert b"Login" in response.data
    assert b"Register" in response.data

def test_role_based_access(client, app):
    """Test that role decorators correctly block unauthorized users and allow authorized ones."""
    # 1. Register users via client with real passwords (so password hashing is correct)
    client.post('/register', data={
        'name': 'Student User', 
        'reg_number': 'S001', 
        'email': 'student@susl.lk', 
        'password': 'Password123', 
        'confirm_password': 'Password123'
    })
    client.post('/register', data={
        'name': 'Admin User', 
        'reg_number': 'A001', 
        'email': 'admin@susl.lk', 
        'password': 'Password123', 
        'confirm_password': 'Password123'
    })
    client.post('/register', data={
        'name': 'Counselor User', 
        'reg_number': 'C001', 
        'email': 'counselor@susl.lk', 
        'password': 'Password123', 
        'confirm_password': 'Password123'
    })

    # 2. Update their roles in database to admin and counselor
    with app.app_context():
        u_admin = User.query.filter_by(email='admin@susl.lk').first()
        assert u_admin is not None
        u_admin.role = 'admin'
        
        u_counselor = User.query.filter_by(email='counselor@susl.lk').first()
        assert u_counselor is not None
        u_counselor.role = 'counselor'
        
        db.session.commit()

    # 3. Test student access
    client.post('/login', data={'email': 'student@susl.lk', 'password': 'Password123'})
    
    response = client.get('/admin/test')
    assert response.status_code == 403  # Student cannot access admin
    
    response = client.get('/counselor/test')
    assert response.status_code == 403  # Student cannot access counselor
    
    client.get('/logout')

    # 4. Test admin access
    client.post('/login', data={'email': 'admin@susl.lk', 'password': 'Password123'})
    
    response = client.get('/admin/test')
    assert response.status_code == 200
    assert b"Admin Access Granted" in response.data
    
    response = client.get('/counselor/test')
    assert response.status_code == 403  # Admin cannot access counselor
    
    client.get('/logout')

    # 5. Test counselor access
    client.post('/login', data={'email': 'counselor@susl.lk', 'password': 'Password123'})
    
    response = client.get('/counselor/test')
    assert response.status_code == 200
    assert b"Counselor Access Granted" in response.data
    
    response = client.get('/admin/test')
    assert response.status_code == 403  # Counselor cannot access admin

