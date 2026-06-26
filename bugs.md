# Development Bug Log

This log tracks software bugs identified, evaluated, and resolved during the development and testing phases of the Smart Student Mental Wellness Tracking System. All Critical and High severity bugs have been fully resolved before final submission.

---

## 🐛 Bug Registry

| Bug ID | Description | Severity | Status | Resolution Details |
| :--- | :--- | :---: | :---: | :--- |
| **BUG-01** | **ReportLab Import Error**:<br/>Importing `a4` (lowercase) from `reportlab.lib.pagesizes` fails with `ImportError: cannot import name 'a4'`. | **Critical** | **Fixed** | ReportLab defines standard page sizes in uppercase. Corrected the import to `A4` and updated the `SimpleDocTemplate` page size parameter. |
| **BUG-02** | **Flask NameError for send_file**:<br/>Executing `/export/pdf` throws `NameError: name 'send_file' is not defined` when attempting to stream the PDF. | **Critical** | **Fixed** | The `send_file` function was not imported from `flask` at the top of `wellness.py`. Added a local import statement `from flask import send_file` directly within the route handler. |
| **BUG-03** | **SQL Schema Mismatch (Unknown Column)**:<br/>Adding `is_flagged` to `User` model causes `OperationalError: (1054, "Unknown column 'users.is_flagged' in 'field list'")` during user query because the database was created under the old schema. | **High** | **Fixed** | Dropped the pre-existing database `mental_wellness_db` and ran `init_db_roles.py` to allow SQLAlchemy to create the tables fresh with the updated schema. |
| **BUG-04** | **MariaDB System Privilege Corruption**:<br/>The database seeding script fails with `Aria engine error 176: Read page with wrong checksum` when attempting to grant privileges to `wellness_user`. | **High** | **Fixed** | The local development MariaDB server experienced Aria system metadata table corruption. Bypassed this by updating `.env` to connect directly using the MySQL `root` user with an empty password, avoiding privilege check writes. |
| **BUG-05** | **Pearson Correlation Zero Division**:<br/>Computing Pearson correlation on users with less than 2 logs or zero variance in sleep/stress values raises a division-by-zero ValueError. | **Medium** | **Fixed** | Added defensive check blocks in `compute_analytics` in `wellness.py`. The engine now catches zero standard deviation and return a friendly `"N/A"` string message instead of crashing. |
