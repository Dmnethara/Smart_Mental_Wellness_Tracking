# Smart Student Mental Wellness Tracking & Analytics System

An advanced, secure web-based mental health tracking and data science analytics system built for students, administrators, and counselors. The system offers interactive dashboards, custom analytics (descriptive statistics, Pearson correlation, weekly stress profiling), a rule-based clinical risk engine, and secure reports (CSV and PDF exports).

---

## 🚀 Key Features

* **Secure Authentication System:** Implementations of password hashing (Flask-Bcrypt) and CSRF protection (Flask-WTF). Includes active session timeouts (2-hour auto-logout).
* **Daily Wellness Logging (CRUD):** Sliders to record Mood, Stress, Sleep Hours, Sleep Quality, and Academic Workload. Features server-side range validation and log ownership check.
* **Interactive Student Dashboard:** Visualizes logs using Chart.js (daily mood trend, weekly stress levels, sleep-stress correlation, and wellness index progression).
* **Data Science Engine:** Calculates mean, median, standard deviation using **Pandas**; evaluates Pearson correlation coefficient ($r$) using **SciPy**; groups weekly logs by day to locate peak stress; and runs a 4-rule Clinical Risk Engine.
* **Admin / Counselor Panel:** Overview of all students, at-risk highlights, aggregated analytics, and detailed student metrics.
* **Privacy by Design:** Student diary notes are strictly deferred in queries and masked in administrative views using SQLAlchemy `defer` to ensure client confidentiality.
* **CSV & PDF Export:** One-click CSV downloads for raw student data, and multi-page styled PDF reports generated via `reportlab`.

---

## 🛠️ Prerequisites

* **Python 3.x** (3.8 - 3.13 recommended)
* **MySQL Server** (via XAMPP, WampServer, Docker, or standalone service)
* Modern web browser (Chrome, Firefox, Edge, etc.)

---

## 💻 Installation & Setup

Follow these steps to set up and run the project locally:

### 1. Clone & Navigate to Project
```bash
git clone https://github.com/Dmnethara/Smart_Mental_Wellness_Tracking.git
cd Smart_Mental_Wellness_Tracking
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a file named `.env` in the root directory (already ignored by Git) and add:
```env
SECRET_KEY=your-custom-secure-secret-key-12345
DATABASE_URL=mysql+pymysql://wellness_user:wellness_pass@localhost/mental_wellness_db
FLASK_ENV=development
FLASK_DEBUG=True
```

### 5. Setup MySQL Database
Ensure your MySQL service is running (e.g. from XAMPP Control Panel click "Start" next to MySQL).
Then, configure the database and user privileges:
```bash
python create_db.py
```
*Note: This script drops any existing database named `mental_wellness_db` and configures `wellness_user` with password `wellness_pass` granting full permissions.*

### 6. Initialize Tables & Seed Role Accounts
Initialize the database tables and seed default accounts for evaluation:
```bash
python init_db_roles.py
```

### 7. Run the Application
Start the Flask development server:
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your web browser.

---

## 👤 Test Accounts (For Evaluation)

You can log in using these pre-seeded credentials or register a new student account:

| Role | Email | Password | Access Details |
| :--- | :--- | :--- | :--- |
| **System Admin** | `admin@susl.ac.lk` | `AdminPass1` | Accesses Admin Dashboard, Registry, Analytics & Alerts |
| **Counselor** | `counselor@susl.ac.lk` | `CounselorPass1` | Accesses Counselor Dashboard, Registry, Analytics & Alerts |
| **Student** | *(Register a new account)* | *User defined* | Logs daily metrics, view history, and export CSV/PDF |

---

## 🧪 Testing

To run the automated pytest test suite (unit and integration tests):
```bash
python -m pytest
```
*The project features 26 automated tests verifying database encryption, route permissions, risk engine calculations, and CRUD validations.*
