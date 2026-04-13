"""Konstanten und Konfiguration für die AI Agent App."""
import os
from pathlib import Path

# Basis-Verzeichnis
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHAT_HISTORY_DIR = DATA_DIR / "chat_history"

# JSON-Dateipfade
USERS_FILE = DATA_DIR / "users.json"
PENDING_APPROVALS_FILE = DATA_DIR / "pending_approvals.json"

# Passwort-Hashing Constants (for PBKDF2)
PASSWORD_HASH_ALGORITHM = "sha256"
PASSWORD_HASH_ITERATIONS = 100000
PASSWORD_HASH_SALT_LENGTH = 32  # bytes

# Admin-Credentials
ADMIN_PASSWORD_SECRET_KEY = "APP_PASSWORD"

# Streamlit Config
PAGE_CONFIG = {
    "page_title": "AI Agent",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

PAGE_CONFIG_LOGIN = {
    "page_title": "AI Agent - Login",
    "layout": "centered"
}

# Session State Keys
SESSION_KEY_USER_ID = "user_id"
SESSION_KEY_USERNAME = "username"
SESSION_KEY_AUTHENTICATED = "authenticated"
SESSION_KEY_CURRENT_CHAT_SESSION = "current_chat_session_uuid"
