"""Authentifizierungs- und Benutzerverwaltungssystem."""
import json
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Tuple

from .constants import (
    USERS_FILE,
    PENDING_APPROVALS_FILE,
    PASSWORD_HASH_ALGORITHM,
    PASSWORD_HASH_ITERATIONS,
    PASSWORD_HASH_SALT_LENGTH,
    DATA_DIR,
)


def _ensure_data_files():
    """Stelle sicher, dass die JSON-Dateien existieren."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not USERS_FILE.exists():
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

    if not PENDING_APPROVALS_FILE.exists():
        with open(PENDING_APPROVALS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


def _hash_password(password: str) -> str:
    """
    Hashiere ein Passwort mit PBKDF2.

    Returns: "salt$hash" Format für Speicherung
    """
    salt = secrets.token_hex(PASSWORD_HASH_SALT_LENGTH)
    hash_obj = hashlib.pbkdf2_hmac(
        PASSWORD_HASH_ALGORITHM,
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PASSWORD_HASH_ITERATIONS
    )
    password_hash = hash_obj.hex()
    return f"{salt}${password_hash}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verifiziere ein Passwort gegen seinen Hash."""
    try:
        salt, password_hash = stored_hash.split('$', 1)
        hash_obj = hashlib.pbkdf2_hmac(
            PASSWORD_HASH_ALGORITHM,
            password.encode('utf-8'),
            salt.encode('utf-8'),
            PASSWORD_HASH_ITERATIONS
        )
        computed_hash = hash_obj.hex()
        return computed_hash == password_hash
    except Exception:
        return False


def _get_timestamp() -> str:
    """Gebe aktuellen Timestamp im ISO-Format."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _load_json(filepath: Path) -> Dict:
    """Lade JSON-Datei."""
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_json(filepath: Path, data: Dict) -> None:
    """Speichere JSON-Datei."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_user(username: str, password: str) -> Tuple[bool, str]:
    """
    Registriere einen neuen Benutzer (wartet auf Admin-Genehmigung).

    Returns: (success: bool, message: str)
    """
    _ensure_data_files()

    # Validierung
    if not username or not password:
        return False, "❌ Alle Felder erforderlich."

    if len(username) < 3:
        return False, "❌ Username muss mindestens 3 Zeichen lang sein."

    if len(password) < 4:
        return False, "❌ Passwort muss mindestens 4 Zeichen lang sein."

    # Prüfe ob Username bereits existiert
    users = _load_json(USERS_FILE)
    pending = _load_json(PENDING_APPROVALS_FILE)

    for user in users.values():
        if user.get('username', '').lower() == username.lower():
            return False, "❌ Username existiert bereits."

    for pending_user in pending.values():
        if pending_user.get('username', '').lower() == username.lower():
            return False, "❌ Registrierung unter diesem Username läuft noch."

    # Erstelle neuen Pending User
    new_uuid = str(uuid.uuid4())
    pending[new_uuid] = {
        "uuid": new_uuid,
        "username": username,
        "password_hash": _hash_password(password),
        "created_at": _get_timestamp()
    }

    _save_json(PENDING_APPROVALS_FILE, pending)
    return True, f"✅ Registrierung erfolgreich! Der Admin muss deine Anfrage genehmigen."


def login_user(username: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """
    Authentifiziere einen Benutzer.

    Returns: (success: bool, message: str, user_uuid: Optional[str])
    """
    _ensure_data_files()

    users = _load_json(USERS_FILE)

    # Finde User nach Username
    user_data = None
    user_uuid = None
    for uid, user in users.items():
        if user.get('username', '').lower() == username.lower():
            user_data = user
            user_uuid = uid
            break

    if not user_data:
        return False, "❌ Username oder Passwort falsch.", None

    # Prüfe Passwort
    if not _verify_password(password, user_data.get('password_hash', '')):
        return False, "❌ Username oder Passwort falsch.", None

    # Prüfe Status - akzeptiere "approved" und "admin"
    status = user_data.get('status')
    if status not in ('approved', 'admin'):
        return False, "❌ Dein Account wurde noch nicht genehmigt.", None

    return True, f"✅ Willkommen, {username}!", user_uuid


def approve_user(pending_uuid: str) -> Tuple[bool, str]:
    """
    Genehmige einen anstehenden Benutzer (Admin-Aktion).

    Returns: (success: bool, message: str)
    """
    _ensure_data_files()

    pending = _load_json(PENDING_APPROVALS_FILE)
    users = _load_json(USERS_FILE)

    if pending_uuid not in pending:
        return False, "❌ Benutzer nicht gefunden."

    pending_user = pending[pending_uuid]

    # Verschiebe zu Users
    users[pending_uuid] = {
        **pending_user,
        "status": "approved",
        "approved_at": _get_timestamp()
    }

    # Entferne aus Pending
    del pending[pending_uuid]

    _save_json(USERS_FILE, users)
    _save_json(PENDING_APPROVALS_FILE, pending)

    return True, f"✅ Benutzer '{pending_user.get('username')}' genehmigt."


def reject_user(pending_uuid: str) -> Tuple[bool, str]:
    """
    Lehne einen anstehenden Benutzer ab (Admin-Aktion).

    Returns: (success: bool, message: str)
    """
    _ensure_data_files()

    pending = _load_json(PENDING_APPROVALS_FILE)

    if pending_uuid not in pending:
        return False, "❌ Benutzer nicht gefunden."

    username = pending[pending_uuid].get('username', 'Unbekannt')
    del pending[pending_uuid]

    _save_json(PENDING_APPROVALS_FILE, pending)

    return True, f"✅ Anfrage von '{username}' abgelehnt."


def get_pending_users() -> Dict:
    """Hole alle ausstehenden Benutzer."""
    _ensure_data_files()
    return _load_json(PENDING_APPROVALS_FILE)


def get_all_users() -> Dict:
    """Hole alle genehmigten Benutzer."""
    _ensure_data_files()
    return _load_json(USERS_FILE)


def get_user_info(user_uuid: str) -> Optional[Dict]:
    """Hole Benutzerinformationen nach UUID."""
    _ensure_data_files()
    users = _load_json(USERS_FILE)
    return users.get(user_uuid)


def is_admin(user_uuid: str) -> bool:
    """Prüfe ob ein Benutzer Admin ist."""
    _ensure_data_files()
    user_info = get_user_info(user_uuid)
    return user_info is not None and user_info.get('status') == 'admin'


def delete_user(user_uuid: str) -> Tuple[bool, str]:
    """
    Lösche einen Benutzer (Admin-Aktion).

    Returns: (success: bool, message: str)
    """
    _ensure_data_files()

    users = _load_json(USERS_FILE)

    if user_uuid not in users:
        return False, "❌ Benutzer nicht gefunden."

    username = users[user_uuid].get('username', 'Unbekannt')
    del users[user_uuid]

    _save_json(USERS_FILE, users)

    return True, f"✅ Benutzer '{username}' gelöscht."
