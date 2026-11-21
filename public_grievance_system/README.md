# Public Grievance Management System

A responsive civic service portal branded CivicConnect, built with Python, Flask, Jinja, vanilla JavaScript and SQLite. Citizens can create accounts, report local issues, follow status history, update profile details and leave feedback after resolution. Administrators can review reports, assign departments, record decisions, and inspect actual complaint analytics and feedback.

## Architecture

- `app.py` contains the Flask application factory, HTTP routes, authorization checks, validation and workflow logic.
- `database.py` owns SQLite connection handling, schema creation, foreign key enforcement and initial department records.
- `config.py` centralizes paths, upload constraints and application settings.
- `templates/` contains the shared layout and page templates, including the citizen profile, role-aware navigation, and reusable complaint timeline.
- `static/css/style.css` provides the CivicConnect responsive visual system; `static/js/script.js` handles mobile navigation, password visibility, registration validation, complaint filters, image preview/drop, dismissible notices, and loading feedback.
- `database/init_db.py` initializes the database. `seed_admin.py` creates an administrator using a password hash, without a public registration route.
- `instance/grievances.db` is created locally on first run and should remain private.

## Features

- Citizen registration with duplicate email checks, password hashing and session login.
- Separate administrator role, seeded locally; role checks protect administrator pages.
- Complaint IDs, private owner-scoped views and status history.
- Image attachments for PNG, JPG, JPEG and WEBP, limited to 5 MB.
- Department assignment, status and remark updates, search and filters.
- One feedback entry per resolved complaint, rating 1–5.
- Profile contact detail and password updates using the existing user record (no database schema changes).
- Home and administrator statistics derived from SQLite records.
- CSRF tokens for all POST forms, parameterized SQLite statements and foreign key constraints.

## Install and run

Python 3.10 or newer is recommended.

```powershell
cd "D:\public events\public_grievance_system"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python database\init_db.py
python seed_admin.py
python app.py
```

Open `http://127.0.0.1:5000`. For local deployment, set a private secret key before starting:

```powershell
$env:FLASK_SECRET_KEY = "replace-with-a-long-random-value"
python app.py
```

Seed the administrator by entering an email and a password of at least 12 characters when prompted. Or set `ADMIN_EMAIL`, `ADMIN_PASSWORD` and optionally `ADMIN_NAME` before running `python seed_admin.py`. Keep those credentials private.

## Main pages

| URL | Purpose |
| --- | --- |
| `/` | Public landing page and service overview |
| `/about` | Project introduction, mission, vision and benefits |
| `/services` | Public issue categories |
| `/how-it-works` | Eight-step complaint journey |
| `/contact` | Portal contact form; messages are saved in SQLite |
| `/register`, `/login` | Citizen registration and sign-in |
| `/citizen/dashboard` | Citizen's private dashboard |
| `/profile` | Update citizen contact details or password |
| `/complaints/new` | Submit a complaint |
| `/complaints/my` | View the citizen's complaint list |
| `/complaints/track` | Track an owned complaint by ID |
| `/admin/login` | Administrator sign-in page |
| `/admin/dashboard` | Administrator overview |
| `/admin/complaints` | Search and filter all complaints |
| `/admin/departments` | View departments and add more |

Password recovery, stored notifications, user-management administration, and administrator settings are not implemented because the existing backend has no corresponding data or routes. The frontend does not present those items as working features.

## Operational notes

Use HTTPS, a strong randomly generated `FLASK_SECRET_KEY`, and `FLASK_DEBUG` unset in any deployment beyond a local demonstration. Back up `instance/grievances.db` and protect the local upload directory. The app binds to Flask's development server by default and is intended for a local project/demo; production hosting should use a production WSGI server.


## Multi-page routes

- / home, /about, /services, /how-it-works, and /contact are separate public pages.
- /login, /register, and /admin/login provide the separate citizen/admin authentication entry points.
- Canonical protected paths are /citizen/dashboard, /complaints/new, /complaints/my, /complaints/track, /complaints/<complaint_id>, /admin/dashboard, /admin/complaints, /admin/departments, and /feedback/<complaint_id>.
- Contact messages are stored in the contact_messages SQLite table.
- Password reset is not automated because no email delivery service is configured; the login page directs users to portal support.
