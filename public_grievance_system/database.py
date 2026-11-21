import sqlite3
from pathlib import Path
from flask import current_app, g

DEPARTMENTS = [
    ("Public Works Department", "Roads, transport and public infrastructure"),
    ("Water Supply Department", "Water supply and distribution"),
    ("Electricity Department", "Electricity and power infrastructure"),
    ("Sanitation Department", "Garbage, drainage and sanitation"),
    ("Municipal Administration", "Public safety, streetlights and general issues"),
]

def get_db():
    if "db" not in g:
        db_path = current_app.config["DATABASE"]
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      mobile TEXT NOT NULL, address TEXT NOT NULL, password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'citizen' CHECK(role IN ('citizen','admin')), created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS departments (
      id INTEGER PRIMARY KEY, department_name TEXT NOT NULL UNIQUE, description TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS complaints (
      id INTEGER PRIMARY KEY, complaint_id TEXT NOT NULL UNIQUE, user_id INTEGER NOT NULL REFERENCES users(id),
      title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL, location TEXT NOT NULL, area TEXT NOT NULL,
      image_filename TEXT, department_id INTEGER REFERENCES departments(id), status TEXT NOT NULL DEFAULT 'Pending'
        CHECK(status IN ('Pending','In Progress','Resolved','Rejected')), admin_remarks TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS complaint_history (
      id INTEGER PRIMARY KEY, complaint_id INTEGER NOT NULL REFERENCES complaints(id) ON DELETE CASCADE,
      previous_status TEXT, new_status TEXT NOT NULL, remarks TEXT NOT NULL DEFAULT '', updated_by INTEGER REFERENCES users(id),
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS feedback (
      id INTEGER PRIMARY KEY, complaint_id INTEGER NOT NULL UNIQUE REFERENCES complaints(id) ON DELETE CASCADE,
      user_id INTEGER NOT NULL REFERENCES users(id), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
      message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS contact_messages (
      id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL, subject TEXT NOT NULL,
      message TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """)
    db.executemany("INSERT OR IGNORE INTO departments(department_name, description) VALUES (?, ?)", DEPARTMENTS)
    db.commit()

def init_app(app):
    app.teardown_appcontext(close_db)

