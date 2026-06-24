from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from sqlalchemy import event

# Initialize SQLAlchemy
db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    reg_number = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.Enum('student', 'admin', 'counselor', name='user_roles'), nullable=False, default='student')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Relationship with wellness logs
    logs = db.relationship('WellnessLog', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

class WellnessLog(db.Model):
    __tablename__ = 'wellness_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    log_date = db.Column(db.Date, nullable=False)
    mood_score = db.Column(db.Integer, nullable=False)  # 1 to 5
    stress_level = db.Column(db.Integer, nullable=False)  # 1 to 5
    sleep_hours = db.Column(db.Numeric(3, 1), nullable=False)  # e.g., 7.5
    sleep_quality = db.Column(db.Integer, nullable=False)  # 1 to 5
    academic_workload = db.Column(db.Integer, nullable=False)  # 1 to 5
    notes = db.Column(db.Text, nullable=True)
    wellness_score = db.Column(db.Numeric(5, 2), nullable=False, default=0.0)  # Computed 20.0 to 100.0
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<WellnessLog {self.log_date} - User {self.user_id} - Score {self.wellness_score}>"

# SQLAlchemy Event Listener to automatically compute the wellness_score
@event.listens_for(WellnessLog, 'before_insert')
@event.listens_for(WellnessLog, 'before_update')
def calculate_wellness_score(mapper, connection, target):
    """
    Computes wellness_score based on mood, stress, sleep quality, and academic workload.
    Formula maps the sum of positive indicators (mood, sleep quality) and 
    inverted negative indicators (6 - stress, 6 - workload) to a scale of 20 to 100.
    """
    try:
        mood = int(target.mood_score)
        stress = int(target.stress_level)
        sleep = int(target.sleep_quality)
        workload = int(target.academic_workload)
        
        # Verify scores are in valid 1-5 range
        for val in [mood, stress, sleep, workload]:
            if not (1 <= val <= 5):
                raise ValueError("Scores must be between 1 and 5")
                
        # Calculate score: sum ranges from 4 to 20. Multiplying by 5 maps it to 20 to 100.
        target.wellness_score = (mood + (6 - stress) + sleep + (6 - workload)) * 5.0
    except (TypeError, ValueError) as e:
        # Fallback in case of invalid or missing values
        target.wellness_score = 0.0
