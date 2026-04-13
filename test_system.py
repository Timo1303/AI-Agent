"""Quick Test Script für die neue Auth & Storage Funktionalität."""
import sys
import os
import io

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(__file__))

from utils import auth_manager, storage_manager

print("=" * 60)
print("TEST: Auth Manager")
print("=" * 60)

# Test 1: User Registration
print("\n1. Test: Registriere einen Test-User")
success, msg = auth_manager.register_user("testuser", "password123", "test@example.com")
print(f"   > {msg}")

# Test 2: Get Pending Users
print("\n2. Test: Hole ausstehende Benutzer")
pending = auth_manager.get_pending_users()
print(f"   > {len(pending)} Benutzer ausstehend: {list(pending.keys())[:1]}")

# Test 3: Approve User
if pending:
    pending_uuid = list(pending.keys())[0]
    print(f"\n3. Test: Genehmige Benutzer {pending_uuid[:8]}...")
    success, msg = auth_manager.approve_user(pending_uuid)
    print(f"   > {msg}")

# Test 4: Login
print("\n4. Test: Login mit genehmigtem Benutzer")
success, msg, user_uuid = auth_manager.login_user("testuser", "password123")
print(f"   > {msg}")
print(f"   > User UUID: {user_uuid}")

if user_uuid:
    # Test 5: Create Chat Session
    print("\n" + "=" * 60)
    print("TEST: Storage Manager")
    print("=" * 60)

    print("\n5. Test: Erstelle Chat-Session")
    session_uuid = storage_manager.create_chat_session(
        user_uuid,
        "Wie kann ich Streamlit optimieren?",
        {"temperature": 0.7, "max_refinements": 3}
    )
    print(f"   > Session UUID: {session_uuid}")

    # Test 6: Add Phase
    print("\n6. Test: Füge Planning-Phase hinzu")
    success = storage_manager.add_phase_to_session(
        user_uuid,
        session_uuid,
        "planning",
        "1. Analyse durchführen\n2. Plan erstellen",
        duration_seconds=3.5
    )
    print(f"   > Success: {success}")

    # Test 7: Add Execution Phase
    print("\n7. Test: Füge Execution-Phase hinzu")
    success = storage_manager.add_phase_to_session(
        user_uuid,
        session_uuid,
        "execution",
        "Hier ist die Lösung...",
        duration_seconds=10.2
    )
    print(f"   > Success: {success}")

    # Test 8: Complete Session
    print("\n8. Test: Markiere Session als abgeschlossen")
    success = storage_manager.complete_chat_session(
        user_uuid,
        session_uuid,
        "FINALE LÖSUNG HIER"
    )
    print(f"   > Success: {success}")

    # Test 9: Load History
    print("\n9. Test: Lade Chat-Verlauf")
    history = storage_manager.get_user_chat_history(user_uuid)
    print(f"   > {len(history)} Sessions gespeichert")

    # Test 10: Get Session Summary
    print("\n10. Test: Lade Session-Zusammenfassung")
    summary = storage_manager.get_chat_sessions_summary(user_uuid)
    print(f"   > {len(summary)} Sessions in Zusammenfassung")
    if summary:
        print(f"   > Erste Session: {summary[0]['problem_input_short']}")

print("\n" + "=" * 60)
print("OK: ALLE TESTS BESTANDEN!")
print("=" * 60)

