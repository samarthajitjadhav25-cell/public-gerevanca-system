# Public Grievance Management System

A Flask and SQLite portal for citizens to submit and track public service complaints, and for administrators to manage reports and departments.

The full feature list, routes, setup notes, and operational guidance are in [`public_grievance_system/README.md`](public_grievance_system/README.md).

## Run locally

```powershell
cd public_grievance_system
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python database\init_db.py
python seed_admin.py
python app.py
```
