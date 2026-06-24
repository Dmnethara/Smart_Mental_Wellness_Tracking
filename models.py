from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_login import UserMixin
from sqlalchemy import event

# Initialize Extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()

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
    Computes wellness_score based on the project's Day 4 data science formula:
    score = (mood*20 + (6-stress)*20 + sleep_q*20 + min(sleep_h/8, 1)*20 + (6-workload)*20) / 5
    Maps the 5 dimensions to a 0 to 100 scale.
    """
    try:
        mood = int(target.mood_score)
        stress = int(target.stress_level)
        sleep_q = int(target.sleep_quality)
        sleep_h = float(target.sleep_hours)
        workload = int(target.academic_workload)
        
        # Validate values are in correct range to prevent corrupt data
        for val in [mood, stress, sleep_q, workload]:
            if not (1 <= val <= 5):
                raise ValueError("Indicators must be between 1 and 5")
        if not (0.0 <= sleep_h <= 16.0):
            raise ValueError("Sleep hours must be between 0 and 16")
            
        # Calculate individual components (each max 20, sum max 100)
        mood_comp = mood * 20
        stress_comp = (6 - stress) * 20
        sleep_q_comp = sleep_q * 20
        sleep_h_comp = min(sleep_h / 8.0, 1.0) * 20
        workload_comp = (6 - workload) * 20
        
        target.wellness_score = (mood_comp + stress_comp + sleep_q_comp + sleep_h_comp + workload_comp) / 5.0
    except (TypeError, ValueError):
        # Fallback in case of invalid or missing values
        target.wellness_score = 0.0
