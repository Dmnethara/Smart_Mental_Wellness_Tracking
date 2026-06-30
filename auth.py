import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, bcrypt

# Create Blueprint
auth = Blueprint('auth', __name__)

def is_valid_password(password):
    """
    Validates that a password is at least 8 characters long 
    and contains at least one numeric digit.
    """
    if len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    return True

@auth.route('/register', methods=['GET', 'POST'])
def register():
    # Redirect to home if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        reg_number = request.form.get('reg_number', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation checks
        if not name or not reg_number or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template('register.html')
            
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html')
            
        if not is_valid_password(password):
            flash("Password must be at least 8 characters long and contain at least 1 number.", "danger")
            return render_template('register.html')
            
        # Check for duplicate email
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("An account with this email already exists.", "danger")
            return render_template('register.html')
            
        # Check for duplicate registration number
        existing_reg = User.query.filter_by(reg_number=reg_number).first()
        if existing_reg:
            flash("An account with this registration number already exists.", "danger")
            return render_template('register.html')
            
        # Hash password and save new user
        # Security criteria: Always decode the hash to string before storing
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        
        new_user = User(
            name=name,
            reg_number=reg_number,
            email=email,
            password_hash=password_hash,
            role='student',  # Default role
            is_active=True
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "danger")
            
    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    # Redirect to home if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash("Please provide both email and password.", "danger")
            return render_template('login.html')
            
        # Retrieve user and verify password
        user = User.query.filter_by(email=email).first()
        
        # NEVER compare plaintext, verify using bcrypt.check_password_hash
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash("This account has been deactivated. Please contact support.", "danger")
                return render_template('login.html')
                
            login_user(user)
            session.permanent = True
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
            
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))

# Test routes for role-based access verification
from decorators import admin_required, counselor_required

@auth.route('/admin/test')
@admin_required
def admin_test():
    return "Admin Access Granted"

@auth.route('/counselor/test')
@counselor_required
def counselor_test():
    return "Counselor Access Granted"
