# Project Progress Log - Smart Mental Wellness Tracking

## Student Details
* **Student Name:** Nethara Vidmanthi
* **Registration Number:** 23CDS0847
* **Degree Program:** Data Science
* **University:** Sabaragamuwa University of Sri Lanka

---

## Day 1: Project Setup & Environment
* **Date:** 2026-06-25
* **Milestones:**
  * Created project folder structure with `templates/`, `static/css/`, `static/js/`, `static/charts/`, `docs/`, and `instance/`.
  * Verified virtual environment `venv/`.
  * Installed core dependencies: `flask`, `flask-login`, `flask-sqlalchemy`, `flask-bcrypt`, `pymysql`, `python-dotenv`, `reportlab`, `matplotlib`, `pandas`, `pytest`.
  * Generated [requirements.txt](file:///c:/Users/user/Desktop/Wellness%20Tracking%20system/Smart_Mental_Wellness_Tracking/requirements.txt).
  * Implemented Flask application factory pattern in [app.py](file:///c:/Users/user/Desktop/Wellness%20Tracking%20system/Smart_Mental_Wellness_Tracking/app.py).
  * Created configuration loading in [config.py](file:///c:/Users/user/Desktop/Wellness%20Tracking%20system/Smart_Mental_Wellness_Tracking/config.py).
  * Set up environment variables in [.env](file:///c:/Users/user/Desktop/Wellness%20Tracking%20system/Smart_Mental_Wellness_Tracking/.env) (ignored by Git).
  * Tested and verified Flask hello world `/` endpoint returns "System Online" on port 5000.

## Day 2: Database Design & MySQL Setup
* **Date:** 2026-06-25
* **Milestones:**
  * Started MySQL (MariaDB) instance from XAMPP (`C:\xampp\mysql\bin\mysqld.exe`).
  * Created database `mental_wellness_db` with `utf8mb4` encoding.
  * Created dedicated database user `wellness_user` with password `wellness_pass` and granted privileges.
  * Designed relational database schema:
    * `users` table: PK, name, email (unique), password_hash, reg_number (unique), role (student/admin/counselor), created_at, is_active.
    * `wellness_logs` table: PK, user_id (FK), log_date, mood_score, stress_level, sleep_hours, sleep_quality, academic_workload, notes, wellness_score (computed), created_at.
  * Implemented database models in [models.py](file:///c:/Users/user/Desktop/Wellness%20Tracking%20system/Smart_Mental_Wellness_Tracking/models.py).
  * Integrated an automatic `wellness_score` calculation listener mapping indicators to a 20-100 scale.
  * Successfully initialized and verified tables in MySQL database.
