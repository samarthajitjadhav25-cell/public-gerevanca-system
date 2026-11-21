"""Create the initial administrator without exposing public admin registration.

Usage: python seed_admin.py
Set ADMIN_EMAIL and ADMIN_PASSWORD before running in a real deployment.
"""
import os
from getpass import getpass
from werkzeug.security import generate_password_hash
from app import create_app
from database import get_db

app = create_app()
with app.app_context():
    email = os.environ.get("ADMIN_EMAIL") or input("Administrator email: ").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD") or getpass("Administrator password (min 12 characters): ")
    name = os.environ.get("ADMIN_NAME", "Portal Administrator").strip()
    if len(password) < 12:
        raise SystemExit("Choose a password with at least 12 characters.")
    try:
        get_db().execute("INSERT INTO users(full_name,email,mobile,address,password_hash,role) VALUES(?,?,?,?,?,'admin')",
                         (name,email,"0000000000","Administration",generate_password_hash(password)))
        get_db().commit()
        print(f"Administrator account created for {email}")
    except Exception as error:
        raise SystemExit(f"Could not create administrator: {error}")
