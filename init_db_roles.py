import os
from app import create_app
from models import db, User, bcrypt

def seed_users():
    app = create_app()
    with app.app_context():
        # Ensure database tables exist (if not already created)
        db.create_all()
        
        # Create Admin
        admin_email = "admin@susl.ac.lk"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            admin = User(
                name="System Admin",
                email=admin_email,
                reg_number="ADMIN01",
                role="admin",
                password_hash=bcrypt.generate_password_hash("AdminPass1").decode("utf-8")
            )
            db.session.add(admin)
            print(f"Created Admin account: {admin_email}")
        else:
            print(f"Admin account already exists: {admin_email}")
            
        # Create Counselor
        counselor_email = "counselor@susl.ac.lk"
        counselor = User.query.filter_by(email=counselor_email).first()
        if not counselor:
            counselor = User(
                name="Student Counselor",
                email=counselor_email,
                reg_number="COUNSELOR01",
                role="counselor",
                password_hash=bcrypt.generate_password_hash("CounselorPass1").decode("utf-8")
            )
            db.session.add(counselor)
            print(f"Created Counselor account: {counselor_email}")
        else:
            print(f"Counselor account already exists: {counselor_email}")
            
        db.session.commit()
        print("Role seeding completed successfully.")

if __name__ == "__main__":
    seed_users()
