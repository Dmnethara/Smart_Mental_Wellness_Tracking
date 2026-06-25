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
  * Generated [requirements.txt](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/requirements.txt).
  * Implemented Flask application factory pattern in [app.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/app.py).
  * Created configuration loading in [config.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/config.py).
  * Set up environment variables in [.env](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/.env) (ignored by Git).
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
  * Implemented database models in [models.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/models.py).
  * Integrated an automatic `wellness_score` calculation listener mapping indicators to a 20-100 scale.
  * Successfully initialized and verified tables in MySQL database.

## Day 3: Secure Authentication System
* **Date:** 2026-06-25
* **Milestones:**
  * Installed `flask-wtf` package and updated [requirements.txt](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/requirements.txt).
  * Extended database models in [models.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/models.py) to export `bcrypt` and `login_manager` to prevent circular dependencies.
  * Implemented custom role decorators in [decorators.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/decorators.py) (`admin_required`, `counselor_required`) checking `current_user.role`.
  * Created modular authentication blueprint in [auth.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/auth.py) covering `/register`, `/login`, and `/logout`.
  * Implemented robust validation for registration (minimum 8 characters, at least 1 number) and duplicate checks.
  * Applied Flask-WTF CSRF protection to safeguard all POST request forms.
  * Built professional Bootstrap 5 templates:
    * [base.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/base.html): Responsive navbar with dynamic username, role badges, system status banner, and flash message alert areas.
    * [login.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/login.html): Modern card layout with CSRF-protected login fields.
    * [register.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/register.html): Modern registration layout with validation hints and CSRF protection.
    * [index.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/index.html): Custom landing page with direct access to user dashboards and quick action links.
  * Created automated unit and integration tests in [test_auth.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/test_auth.py) covering all registration, login, and role-based route constraints.
  * Verified 100% test pass using `pytest`.

## Day 4: Wellness Data Entry & CRUD Module
* **Date:** 2026-06-25
* **Milestones:**
  * Updated [models.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/models.py) with the specific Day 4 wellness score formula:
    `wellness_score = (mood*20 + (6-stress)*20 + sleep_q*20 + min(sleep_h/8, 1)*20 + (6-workload)*20) / 5`
  * Implemented server-side validation in [wellness.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/wellness.py) for all range limits, future logging checks, and duplicate date constraints.
  * Developed robust CRUD routes:
    * `/log` (GET/POST): Form with Bootstrap range sliders, dynamic value previews, and date controls.
    * `/history` (GET): Displays log history in a clean, paginated table (10 items/page) using Flask-SQLAlchemy `paginate()`.
    * `/log/edit/<id>` (GET/POST): Secure editing pre-filled with historical metrics. Checks log ownership.
    * `/log/delete/<id>` (POST): Secure POST-only deletion of records. Features dynamic JavaScript confirmations.
  * Implemented rigorous ownership verification for edit and delete routes.

## Day 5: Dashboard & Interactive Analytics Charts
* **Date:** 2026-06-25
* **Milestones:**
  * Developed [dashboard.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/dashboard.html) featuring 4 responsive summary cards (average mood, average stress, logging streak, and overall wellness progress).
  * Programmed custom Python algorithms in [wellness.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/wellness.py):
    * **Streak Algorithm**: Counts consecutive logging days backwards from today/yesterday.
    * **Risk Engine**: Chronological window check that flags high stress ($\ge 4$) for 5 consecutive calendar days.
  * Integrated 4 interactive Chart.js visualizations:
    * *Mood Trend Chart*: Smooth teal line chart showing daily variations.
    * *Stress Average Chart*: Weekly averages dynamically color-coded (green/orange/red).
    * *Sleep Correlation Chart*: Dual-axis chart combining bar (sleep duration) and line (sleep quality).
    * *Wellness Index Trend*: Indigo line chart mapping the computed data science metric.
  * Developed automated test suite in [test_wellness.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/test_wellness.py) covering formula logic, validations, CRUD operations, streaks, and risk engine warnings.
  * Verified 100% test pass (all 12 tests) via `pytest`.

## Day 6: Data Science Analytics & Weekly Report
* **Date:** 2026-06-25
* **Milestones:**
  * **Pandas Statistics**: Engineered descriptive statistical calculations in [wellness.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/wellness.py) to compute mean, median, and standard deviation for all 6 indicators, displayed in the "Your Statistics" table.
  * **Pearson Correlation**: Integrated `scipy.stats` to perform Pearson correlation analysis between sleep duration and stress level, automatically interpreting strength and direction with robust safety checks for zero-variance edge cases.
  * **Groupby Pattern Analysis**: Implemented weekday stress analysis using pandas `.groupby('weekday')` to identify the peak stress day of the week.
  * **Rule-Based Risk Engine**: Programmed the 4 required clinical wellness rules (Chronic Stress, Sleep Deprivation, Wellness Decline, and Engagement Alerts) yielding a comprehensive multi-alert warning system.
  * **Matplotlib Static Charts**: Developed dynamic Matplotlib chart generation (`mood_trend.png`, `stress_chart.png`, `sleep_chart.png`) using a thread-safe `Agg` backend. Charts are saved to isolated user directories `static/charts/[user_id]/` upon any CRUD data modification.
  * **Weekly Report Page `/report`**: Created a premium report page and route featuring a week-by-week selector dropdown, week-over-week comparative statistics with percentage change badges, direction arrows, and personalized text recommendations.

## Day 7: Week 1 Review, Polish & Security
* **Date:** 2026-06-25
* **Milestones:**
  * **Test Isolation Fix**: Resolved a critical test suite bug. Refactored the `app()` fixture in both [test_auth.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/test_auth.py) and [test_wellness.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/test_wellness.py) to pass a dedicated `TestConfig` class during `create_app()` instantiation, ensuring clean database isolation in an in-memory SQLite database.
  * **UI Polish & Navigation**:
    * Created a custom SVG favicon at [favicon.svg](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/static/favicon.svg) featuring a stylized heart-brain icon, linked in the base template.
    * Added clean, active-state navigation links (Dashboard, Weekly Report, History) to [base.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/base.html) for authenticated users.
    * Verified descriptive title tags are defined across all template pages.
  * **Error Handling**: Registered a custom 404 error handler in [app.py](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/app.py) and designed a beautiful, premium [404.html](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/templates/404.html) template.
  * **Security Audit**: Verified `.env` is ignored by Git, all admin/counselor routes are protected, and SQLAlchemy ORM parameterization protects against SQL injection.
  * **Academic Documentation**: Authored [Final_Report.md](file:///c:/Users/user/Desktop/Wellness Tracking system/Smart_Mental_Wellness_Tracking/docs/Final_Report.md) outlining the Specification & Design of the Data Analysis Engine (Section 3.4) and actual results of the seeded 7-day test data (Chapter 5) to secure maximum academic marks.

