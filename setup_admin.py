"""Setup-Script: Erstellt einen Admin-Account für die erste Nutzung."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils import auth_manager
import getpass

print("=" * 60)
print("SETUP: Admin-Account erstellen")
print("=" * 60)

# Check if admin already exists
all_users = auth_manager.get_all_users()
admin_exists = any(user.get('status') == 'admin' for user in all_users.values())

if admin_exists:
    print("\n⚠️  Ein Admin-Account existiert bereits!")
    print("   Wenn du ihn neu erstellen möchtest, lösche zuerst data/users.json")
    sys.exit(1)

print("\nErstelle einen neuen Admin-Account:")
print("-" * 60)

username = input("Admin-Username: ").strip()
if not username or len(username) < 3:
    print("❌ Username ungültig (min. 3 Zeichen)")
    sys.exit(1)

# Check if username already taken
for user in all_users.values():
    if user.get('username', '').lower() == username.lower():
        print(f"❌ Username '{username}' existiert bereits")
        sys.exit(1)

password = getpass.getpass("Admin-Passwort: ")
password_confirm = getpass.getpass("Passwort wiederholen: ")

if password != password_confirm:
    print("❌ Passwörter stimmen nicht überein")
    sys.exit(1)

if len(password) < 4:
    print("❌ Passwort ungültig (min. 4 Zeichen)")
    sys.exit(1)

print("\n" + "=" * 60)

# Create admin account
import uuid
from datetime import datetime, timezone

new_uuid = str(uuid.uuid4())
timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

users = auth_manager.get_all_users()
users[new_uuid] = {
    "uuid": new_uuid,
    "username": username,
    "password_hash": auth_manager._hash_password(password),
    "status": "admin",
    "created_at": timestamp,
    "approved_at": timestamp
}

auth_manager._save_json(auth_manager.USERS_FILE, users)

print("✅ Admin-Account erstellt!")
print(f"   Username: {username}")
print(f"   UUID: {new_uuid}")
print("\n📌 Du kannst dich jetzt auf der Login-Seite anmelden.")
print("=" * 60)
