"""Admin-Panel für die AI Agent App - Verwaltete Benutzer und Genehmigungen."""
import streamlit as st
import os
from dotenv import load_dotenv
import sys

# Importiere Utils
sys.path.insert(0, str(os.path.dirname(__file__)))
from utils import auth_manager
from utils.constants import ADMIN_PASSWORD_SECRET_KEY

load_dotenv()

# ==================== ADMIN AUTHENTIFIZIERUNG ====================
def admin_auth_check():
    """Überprüfe Admin-Passwort."""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False

    if not st.session_state.admin_authenticated:
        st.set_page_config(page_title="Admin Panel - Login", layout="centered")
        st.title("🔐 Admin Panel - Login")

        admin_password = st.text_input("Admin-Passwort:", type="password", placeholder="Gib das Admin-Passwort ein")

        if st.button("🔓 Admin-Login", use_container_width=True, type="primary"):
            correct_password = st.secrets.get(ADMIN_PASSWORD_SECRET_KEY, "test123")
            if admin_password == correct_password:
                st.session_state.admin_authenticated = True
                st.success("✅ Willkommen, Admin!")
                st.rerun()
            else:
                st.error("❌ Falsches Admin-Passwort!")

        st.stop()

    return True


admin_auth_check()

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Admin Panel", layout="wide")
st.title("🛠️ Admin Panel")
st.markdown("*Verwende Benutzer und genehmige Registrierungen*")

# Logout Button
col1, col2, col3 = st.columns([6, 1, 1])
with col3:
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.rerun()

st.divider()

# ==================== REITER ====================
tab1, tab2, tab3 = st.tabs(["⏳ Ausstehende Genehmigungen", "👥 Alle Benutzer", "📊 Statistik"])

# TAB 1: Ausstehende Genehmigungen
with tab1:
    st.subheader("⏳ Ausstehende Benutzer-Genehmigungen")

    pending_users = auth_manager.get_pending_users()

    if not pending_users:
        st.info("✅ Keine ausstehenden Genehmigungen.")
    else:
        st.warning(f"⏳ {len(pending_users)} Benutzer warten auf Genehmigung")

        for user_uuid, user_data in pending_users.items():
            with st.container(border=True):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.write(f"**Username:** {user_data.get('username', 'N/A')}")
                    st.write(f"**Email:** {user_data.get('email', 'N/A')}")

                with col2:
                    st.write(f"**Registriert:** {user_data.get('created_at', 'N/A')[:10]}")

                with col3:
                    col_approve, col_reject = st.columns(2)
                    with col_approve:
                        if st.button("✅ Genehmigen", key=f"approve_{user_uuid}", use_container_width=True, type="primary"):
                            success, message = auth_manager.approve_user(user_uuid)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

                    with col_reject:
                        if st.button("❌ Ablehnen", key=f"reject_{user_uuid}", use_container_width=True):
                            success, message = auth_manager.reject_user(user_uuid)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)

# TAB 2: Alle Benutzer
with tab2:
    st.subheader("👥 Alle genehmigten Benutzer")

    all_users = auth_manager.get_all_users()

    if not all_users:
        st.info("Noch keine Benutzer vorhanden.")
    else:
        st.write(f"**Insgesamt:** {len(all_users)} Benutzer")

        # Tabelle
        for user_uuid, user_data in sorted(all_users.items(), key=lambda x: x[1].get('created_at', ''), reverse=True):
            with st.container(border=True):
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

                with col1:
                    st.write(f"**Username:** {user_data.get('username', 'N/A')}")

                with col2:
                    st.write(f"**Email:** {user_data.get('email', 'N/A')}")

                with col3:
                    created = user_data.get('created_at', 'N/A')[:10]
                    approved = user_data.get('approved_at', 'N/A')[:10]
                    st.write(f"**Beigetreten:** {created}\n**Genehmigt:** {approved}")

                with col4:
                    if st.button("🗑 Löschen", key=f"delete_{user_uuid}", use_container_width=True, type="secondary"):
                        success, message = auth_manager.delete_user(user_uuid)
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)

# TAB 3: Statistik
with tab3:
    st.subheader("📊 Statistik")

    col1, col2, col3 = st.columns(3)

    all_users = auth_manager.get_all_users()
    pending_users = auth_manager.get_pending_users()

    with col1:
        st.metric("👥 Aktive Benutzer", len(all_users))

    with col2:
        st.metric("⏳ Ausstehende Genehmigungen", len(pending_users))

    with col3:
        st.metric("📝 Insgesamt", len(all_users) + len(pending_users))

    st.divider()

    if all_users:
        st.write("**Zuletzt registrierte Benutzer:**")
        recent_users = sorted(all_users.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:5]
        for user_uuid, user_data in recent_users:
            st.write(f"- {user_data.get('username')} ({user_data.get('created_at', '')[:10]})")
