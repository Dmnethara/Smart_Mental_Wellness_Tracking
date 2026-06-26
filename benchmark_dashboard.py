import time
from datetime import datetime, timedelta
from app import create_app
from models import db, User, WellnessLog
from flask_bcrypt import Bcrypt

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key"

def run_benchmark():
    app = create_app(TestConfig)
    client = app.test_client()
    bcrypt = Bcrypt(app)
    
    print("Initializing Performance Benchmark...")
    
    with app.app_context():
        db.create_all()
        # Clean old benchmark data
        benchmark_email = "benchmark@susl.ac.lk"
        old_user = User.query.filter_by(email=benchmark_email).first()
        if old_user:
            db.session.delete(old_user)
            db.session.commit()
            
        # 1. Seed a benchmark student user
        user = User(
            name="Benchmark Student",
            email=benchmark_email,
            reg_number="BENCH01",
            role="student",
            password_hash=bcrypt.generate_password_hash("BenchPass1").decode("utf-8")
        )
        db.session.add(user)
        db.session.commit()
        
        # 2. Seed 30 days of daily wellness logs
        today = datetime.now().date()
        logs = []
        for i in range(30):
            log_date = today - timedelta(days=i)
            # Create variation in metrics
            mood = 3 + (i % 3 - 1)  # 2, 3, 4
            stress = 3 - (i % 3 - 1)  # 4, 3, 2
            sleep_h = 7.0 + (i % 2 * 1.5 - 0.75)  # 6.25, 7.75
            sleep_q = 3 + (i % 2 * 2 - 1)  # 2, 4
            workload = 3 + (i % 3 - 1)  # 2, 3, 4
            
            log = WellnessLog(
                user_id=user.id,
                log_date=log_date,
                mood_score=mood,
                stress_level=stress,
                sleep_hours=sleep_h,
                sleep_quality=sleep_q,
                academic_workload=workload,
                notes=f"Benchmark day {i}"
            )
            logs.append(log)
            
        db.session.add_all(logs)
        db.session.commit()
        print(f"Seeded 30 days of daily logs for {benchmark_email}.")
        
    # 3. Simulate login
    client.post('/login', data={
        'email': benchmark_email,
        'password': "BenchPass1"
    })
    
    # 4. Measure Dashboard Page Load Time (GET /dashboard)
    # Perform 3 runs to get an average
    runs = 3
    total_time = 0.0
    
    print(f"Running {runs} page load trials...")
    for r in range(runs):
        start_time = time.perf_counter()
        response = client.get('/dashboard')
        end_time = time.perf_counter()
        
        load_time = end_time - start_time
        total_time += load_time
        print(f"  Trial {r+1}: {load_time:.4f} seconds (status {response.status_code})")
        assert response.status_code == 200
        
    avg_time = total_time / runs
    print(f"\nBenchmark Results:")
    print(f"  Average Dashboard Load Time: {avg_time:.4f} seconds")
    print(f"  Performance Target (< 2.0s): {'PASSED' if avg_time < 2.0 else 'FAILED'}")
    
    # Cleanup after benchmark
    with app.app_context():
        user = User.query.filter_by(email=benchmark_email).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            print("Benchmark seed data cleaned up.")

if __name__ == "__main__":
    run_benchmark()
