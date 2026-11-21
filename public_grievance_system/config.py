import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
DATABASE = INSTANCE_DIR / "grievances.db"
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
MAX_CONTENT_LENGTH = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
