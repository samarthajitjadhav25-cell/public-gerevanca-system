
"""Initialize the local SQLite database."""
from app import create_app
from database import init_db

app = create_app()
with app.app_context():
    init_db()
    print(f"Database initialized at {app.config['DATABASE']}")
