"""Authentifizierungs- und Benutzerverwaltungssystem (Supabase Edition)."""
import hashlib
import secrets
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    try:
        import streamlit as st
        SUPABASE_URL = st.secrets.get("SUPABASE_URL")
        SUPABASE_KEY = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

PASSWORD_HASH_ALGORITHM = 'sha256'
PASSWORD_HASH_ITERATIONS = 100000
PASSWORD_HASH_SALT_LENGTH = 16

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(PASSWORD_HASH_SALT_LENGTH)
    hash_obj = hashlib.pbkdf2_hmac(PASSWORD_HASH_ALGORITHM, password.encode('utf-8'), salt.encode('utf-8'), PASSWORD_HASH_ITERATIONS)
    return f"{salt}${hash_obj.hex()}"

def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, password_hash = stored_hash.split('$', 1)
        hash_obj = hashlib.pbkdf2_hmac(PASSWORD_HASH_ALGORITHM, password.encode('utf-8'), salt.encode('utf-8'), PASSWORD_HASH_ITERATIONS)
        return hash_obj.hex() == password_hash
    except Exception:
        return False

def _get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def register_user(username: str, password: str) -> Tuple[bool, str]:
    if not supabase: return False, "❌ Datenbank nicht konfiguriert."
    if not username or not password: return False, "❌ Alle Felder erforderlich."
    if len(username) < 3: return False, "❌ Username muss mindestens 3 Zeichen lang sein."
    if len(password) < 4: return False, "❌ Passwort muss mindestens 4 Zeichen lang sein."

    res_users = supabase.table("users").select("id").ilike("username", username).execute()
    if len(res_users.data) > 0: return False, "❌ Username existiert bereits."

    res_pending = supabase.table("pending_approvals").select("id").ilike("username", username).execute()
    if len(res_pending.data) > 0: return False, "❌ Registrierung unter diesem Username läuft noch."

    supabase.table("pending_approvals").insert({
        "username": username,
        "password_hash": _hash_password(password)
    }).execute()
    
    return True, "✅ Registrierung erfolgreich! Der Admin muss deine Anfrage genehmigen."

def login_user(username: str, password: str) -> Tuple[bool, str, Optional[str]]:
    if not supabase: return False, "❌ Datenbank nicht konfiguriert.", None
    
    res = supabase.table("users").select("*").ilike("username", username).execute()
    if len(res.data) == 0: return False, "❌ Username oder Passwort falsch.", None
    
    user_data = res.data[0]
    if not _verify_password(password, user_data.get('password_hash', '')):
        return False, "❌ Username oder Passwort falsch.", None

    if user_data.get('status') not in ('approved', 'admin'):
        return False, "❌ Dein Account wurde noch nicht genehmigt.", None

    return True, f"✅ Willkommen, {user_data.get('username')}!", user_data.get('id')

def approve_user(pending_uuid: str) -> Tuple[bool, str]:
    if not supabase: return False, "❌ Datenbank."
    res = supabase.table("pending_approvals").select("*").eq("id", pending_uuid).execute()
    if len(res.data) == 0: return False, "❌ Benutzer nicht gefunden."
    
    p = res.data[0]
    supabase.table("users").insert({
        "username": p["username"],
        "password_hash": p["password_hash"],
        "status": "approved",
        "approved_at": _get_timestamp()
    }).execute()
    supabase.table("pending_approvals").delete().eq("id", pending_uuid).execute()
    return True, f"✅ Benutzer '{p['username']}' genehmigt."

def reject_user(pending_uuid: str) -> Tuple[bool, str]:
    if not supabase: return False, ""
    res = supabase.table("pending_approvals").delete().eq("id", pending_uuid).execute()
    return True, "✅ Anfrage abgelehnt."

def get_pending_users() -> Dict:
    if not supabase: return {}
    res = supabase.table("pending_approvals").select("*").execute()
    return {p["id"]: p for p in res.data}

def get_all_users() -> Dict:
    if not supabase: return {}
    res = supabase.table("users").select("*").execute()
    return {u["id"]: u for u in res.data}

def get_user_info(user_uuid: str) -> Optional[Dict]:
    if not supabase: return None
    res = supabase.table("users").select("*").eq("id", user_uuid).execute()
    return res.data[0] if len(res.data) > 0 else None

def is_admin(user_uuid: str) -> bool:
    info = get_user_info(user_uuid)
    return info is not None and info.get('status') == 'admin'

def delete_user(user_uuid: str) -> Tuple[bool, str]:
    if not supabase: return False, ""
    supabase.table("users").delete().eq("id", user_uuid).execute()
    return True, "✅ Benutzer gelöscht."
