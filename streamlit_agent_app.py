import streamlit as st
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import sys

# Importiere Utils
sys.path.insert(0, str(os.path.dirname(__file__)))
from utils import auth_manager, storage_manager
from utils.constants import (
    SESSION_KEY_USER_ID,
    SESSION_KEY_USERNAME,
    SESSION_KEY_AUTHENTICATED,
    SESSION_KEY_CURRENT_CHAT_SESSION,
    PAGE_CONFIG,
    PAGE_CONFIG_LOGIN
)

# ==================== SICHERHEIT & AUTHENTIFIZIERUNG ====================
def auth_check():
    """Überprüfe Authentifizierung und zeige Login/Registrierungs-Formular."""
    if SESSION_KEY_AUTHENTICATED not in st.session_state:
        st.session_state[SESSION_KEY_AUTHENTICATED] = False
        st.session_state[SESSION_KEY_USER_ID] = None
        st.session_state[SESSION_KEY_USERNAME] = None

    if not st.session_state[SESSION_KEY_AUTHENTICATED]:
        st.set_page_config(**PAGE_CONFIG_LOGIN) # type: ignore
        st.title("🔐 AI Agent - Login")

        # Tab: Login / Registrierung
        tab1, tab2 = st.tabs(["🔓 Login", "📝 Registrierung"])

        with tab1:
            st.subheader("Einloggen")
            login_username = st.text_input("Username:", placeholder="Dein Username", key="login_username")
            login_password = st.text_input("Passwort:", type="password", placeholder="Dein Passwort", key="login_password")

            if st.button("🔓 Einloggen", use_container_width=True, type="primary"):
                success, message, user_uuid = auth_manager.login_user(login_username, login_password)
                if success:
                    st.session_state[SESSION_KEY_AUTHENTICATED] = True
                    st.session_state[SESSION_KEY_USER_ID] = user_uuid
                    st.session_state[SESSION_KEY_USERNAME] = login_username
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

        with tab2:
            st.subheader("Neuen Account erstellen")
            st.info("💡 Nach der Registrierung musst du warten, bis der Admin deinen Account genehmigt.")

            reg_username = st.text_input("Username:", placeholder="Wähle einen Username", key="reg_username")
            reg_password = st.text_input("Passwort:", type="password", placeholder="Mindestens 4 Zeichen", key="reg_password")
            reg_password_confirm = st.text_input("Passwort wiederholen:", type="password", placeholder="Bestätige Passwort", key="reg_password_confirm")

            if st.button("📝 Registrieren", use_container_width=True, type="primary"):
                if reg_password != reg_password_confirm:
                    st.error("❌ Passwörter stimmen nicht überein.")
                else:
                    success, message = auth_manager.register_user(reg_username, reg_password)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

        st.stop()

    return True


# ==================== API SETUP ====================
load_dotenv()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY") or st.secrets.get("NVIDIA_API_KEY")

if not NVIDIA_API_KEY:
    st.error("❌ NVIDIA_API_KEY nicht gefunden!")
    st.stop()

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

MODEL = "meta/llama-3.1-70b-instruct"

# ==================== FUNKTIONEN ====================
def query_agent(messages, system_prompt, temperature=0.7, max_tokens=2048, user_temperature=None):
    """Schickt eine Anfrage an die API."""
    if user_temperature is not None:
        temperature = user_temperature

    full_messages = [{"role": "system", "content": system_prompt}] + messages

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Fehler: {str(e)}"

def extract_acceptance(verification_text):
    """Extrahiert, ob die Lösung akzeptabel ist."""
    if not verification_text:
        return False

    text_lower = verification_text.lower()

    positive_indicators = [
        "fazit: ja",
        "ist akzeptabel",
        "wird akzeptiert",
        "kann akzeptiert werden",
        "erfolgreich gelöst"
    ]

    negative_indicators = [
        "fazit: nein",
        "nicht akzeptabel",
        "unzureichend",
        "bedarf weiterer arbeit",
        "muss noch verbessert"
    ]

    for indicator in positive_indicators:
        if indicator in text_lower:
            return not any(neg in text_lower for neg in ["aber", "jedoch", "bedarf"])

    for indicator in negative_indicators:
        if indicator in text_lower:
            return False

    return False

def extract_short_summary(text, max_chars=150):
    """Extrahiert eine sehr kurze Zusammenfassung für den Expander-Title."""
    if not text:
        return "Verarbeitet..."

    lines = text.split('\n')
    summary = ' '.join(lines)
    summary = summary.replace('#', '').replace('**', '').replace('*', '')

    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(' ', 1)[0] + "..."

    return summary.strip()

def plan_phase(user_prompt, user_temperature):
    """Phase 1: Erstellt einen Plan."""
    system_prompt = """Du bist ein Plan-ersteller. DEINE EINZIGE AUFGABE ist es, einen detaillierten Plan zur Lösung des Problems zu erstellen.

WICHTIG: Erstelle NUR einen Plan, keine Lösung!
- Analysiere das Problem
- Erstelle Lösungsschritte
- Definiere Erfolgskriterien

Format:
1. PROBLEM-ANALYSE: Kurze Zusammenfassung
2. LÖSUNGSSCHRITTE: Nummerierte Liste der Schritte
3. ERFOLGS-KRITERIUM: Woran erkenne ich, dass das Problem gelöst ist?

Stoppe nach dem Plan. Fange NICHT mit der Lösung an!"""

    messages = [{"role": "user", "content": f"Erstelle einen Plan für: {user_prompt}"}]
    return query_agent(messages, system_prompt, user_temperature=user_temperature)

def execution_phase(user_prompt, plan, user_temperature):
    """Phase 2: Arbeitet den Plan ab."""
    system_prompt = """Du bist ein Problemlöser. DEINE EINZIGE AUFGABE ist es, den gegebenen Plan Schritt für Schritt UMZUSETZEN.

WICHTIG:
- Folge NUR dem Plan
- Implementiere die Lösungsschritte
- Gib am Ende eine klare ZUSAMMENFASSUNG der Lösung

Erstelle KEINE neuen Pläne, KEINE Überprüfungen - nur die Umsetzung!"""

    messages = [
        {"role": "user", "content": f"""Problem: {user_prompt}

Plan:\n{plan}

Setze diesen Plan Punkt für Punkt um und erstelle die Lösung."""}
    ]

    return query_agent(messages, system_prompt, max_tokens=3000, user_temperature=user_temperature)

def verification_phase(user_prompt, plan, solution, user_temperature):
    """Phase 3: Überprüft die Lösung."""
    system_prompt = """Du bist ein kritischer Reviewer. DEINE EINZIGE AUFGABE ist es, die gegebene Lösung zu überprüfen.

WICHTIG:
- Überprüfe die Lösung NUR gegen den Plan
- Gebe ehrliches Feedback
- Gebe eine Note von 1-10
- Schreibe am Ende genau: "FAZIT: ja, ist akzeptabel" oder "FAZIT: nein, nicht akzeptabel"

NICHT: Erstelle keine neuen Lösungen, keine neuen Pläne!"""

    messages = [
        {"role": "user", "content": f"""Problem: {user_prompt}

Plan: {plan}

Lösung: {solution}

Überprüfe diese Lösung kritisch. Passt sie zum Plan? Ist sie vollständig?"""}
    ]

    verification = query_agent(messages, system_prompt, temperature=0.3, user_temperature=user_temperature)
    is_acceptable = extract_acceptance(verification)

    return verification, is_acceptable

def refinement_phase(user_prompt, plan, solution, feedback, iteration, user_temperature):
    """Phase 4: Verbessert die Lösung."""
    system_prompt = """Du bist ein Verbesserer. DEINE EINZIGE AUFGABE ist es, die Lösung basierend auf Feedback zu optimieren.

WICHTIG:
- Verbessere NUR die vorhandene Lösung
- Nutze das gegebene Feedback
- Erkläre welche Verbesserungen du gemacht hast
- Gib die komplette verbesserte Lösung aus

NICHT: Erstelle keinen neuen Plan, keine neue Strategie!"""

    messages = [
        {"role": "user", "content": f"""Problem: {user_prompt}

Bisherige Lösung: {solution}

Feedback zur Verbesserung: {feedback}

Verbessere die Lösung basierend auf diesem Feedback."""}
    ]

    return query_agent(messages, system_prompt, max_tokens=3000, user_temperature=user_temperature)

# ==================== STREAMLIT UI ====================
auth_check()

st.set_page_config(**PAGE_CONFIG) # type: ignore

st.title("AI Agent - Intelligent Problem Solver")
st.markdown("*Powered by NVIDIA NIM & Llama 3.1 70B*")

# Sidebar mit User-Info
with st.sidebar:
    st.header("⚙️ Einstellungen")

    # User-Info
    st.info(f"👤 Angemeldet als: **{st.session_state[SESSION_KEY_USERNAME]}**")

    # Admin-Badge
    if auth_manager.is_admin(st.session_state[SESSION_KEY_USER_ID]):
        st.success("🔐 **ADMIN-MODUS**")

    if st.button("🚪 Ausloggen", use_container_width=True):
        st.session_state[SESSION_KEY_AUTHENTICATED] = False
        st.session_state[SESSION_KEY_USER_ID] = None
        st.session_state[SESSION_KEY_USERNAME] = None
        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = None
        st.rerun()

    st.divider()

    # Admin-Bereich
    if auth_manager.is_admin(st.session_state[SESSION_KEY_USER_ID]):
        with st.expander("🛠️ Admin-Panel", expanded=False):
            st.subheader("Ausstehende Genehmigungen")
            pending_users = auth_manager.get_pending_users()

            if not pending_users:
                st.info("✅ Keine ausstehenden Genehmigungen")
            else:
                st.warning(f"{len(pending_users)} Benutzer warten")
                for user_uuid, user_data in pending_users.items():
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.write(f"**{user_data.get('username')}**")
                        st.caption(f"Seit: {user_data.get('created_at', '')[:10]}")
                    with col2:
                        col_app, col_rej = st.columns(2)
                        with col_app:
                            if st.button("✅", key=f"app_{user_uuid}", use_container_width=True):
                                auth_manager.approve_user(user_uuid)
                                st.success("Genehmigt!")
                                st.rerun()
                        with col_rej:
                            if st.button("❌", key=f"rej_{user_uuid}", use_container_width=True):
                                auth_manager.reject_user(user_uuid)
                                st.success("Abgelehnt!")
                                st.rerun()

            st.divider()
            st.subheader("Alle Benutzer")
            all_users = auth_manager.get_all_users()
            st.write(f"**{len(all_users)} Benutzer insgesamt**")

            for user_uuid, user_data in sorted(all_users.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:10]:
                col1, col2 = st.columns([2, 1])
                with col1:
                    status_badge = "🔐 Admin" if user_data.get('status') == 'admin' else "👤 User"
                    st.write(f"{status_badge} **{user_data.get('username')}**")
                    st.caption(f"Seit: {user_data.get('created_at', '')[:10]}")
                with col2:
                    if user_data.get('status') != 'admin':
                        if st.button("🗑", key=f"del_{user_uuid}", use_container_width=True):
                            auth_manager.delete_user(user_uuid)
                            st.success("Gelöscht!")
                            st.rerun()

    st.divider()

    max_refinements = st.slider(
        "Max. Verbesserungsiterationen",
        min_value=1,
        max_value=10,
        value=5,
        help="Wie oft soll der Agent die Lösung verbessern?"
    )

    user_temperature = st.slider(
        "Temperatur (Kreativität)",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
        help="0.0 = präzise, 1.0 = kreativ"
    )

    st.divider()

    # Chat-Verlauf Sidebar
    st.subheader("📋 Chat-Verlauf")
    with st.expander("Meine bisherigen Chats", expanded=False):
        chat_history = storage_manager.get_chat_sessions_summary(st.session_state[SESSION_KEY_USER_ID])

        if not chat_history:
            st.caption("Noch keine Chats gespeichert.")
        else:
            for session in chat_history:
                col1, col2 = st.columns([4, 1])
                with col1:
                    if st.button(
                        f"📌 {session['created_at'][:10]}\n{session['problem_input_short']}",
                        key=f"load_chat_{session['id']}",
                        use_container_width=True
                    ):
                        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = session['id']
                        st.rerun()

    st.divider()
    st.info("💡 Der Agent wird dein Problem analysieren, einen Plan erstellen, die Lösung entwickeln und dann überprüfen & verbessern!")

    if st.button("🆕 Neues Problem", use_container_width=True):
        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = None
        if "chat_history" in st.session_state:
            del st.session_state["chat_history"]
        if "problem_result" in st.session_state:
            del st.session_state["problem_result"]
        st.rerun()

# Session State für Verlauf - FRÜH initialisieren (nach auth_check)
if SESSION_KEY_CURRENT_CHAT_SESSION not in st.session_state:
    st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "problem_result" not in st.session_state:
    st.session_state.problem_result = None

# FALL 1: Lade existierenden Chat
if st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION]:
    loaded_session = storage_manager.get_chat_session(
        st.session_state[SESSION_KEY_USER_ID],
        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION]
    )

    if loaded_session:
        st.header(f"📌 Chat vom {loaded_session.get('created_at', '')[:10]}")
        st.write(f"**Problem:** {loaded_session.get('problem_input', '')}")

        st.divider()

        # Zeige alle Phasen
        for phase_data in loaded_session.get("phases", []):
            phase_name = phase_data.get("phase", "")
            phase_output = phase_data.get("output", "")
            duration = phase_data.get("duration_seconds", 0)
            timestamp = phase_data.get("timestamp", "")

            # Nice Phase-Namen
            phase_titles = {
                "planning": "📋 Phase 1: Planung",
                "execution": "🚀 Phase 2: Ausführung",
                "verification": "✅ Phase 3: Überprüfung",
            }

            if "refinement" in phase_name:
                title = f"🔄 {phase_name.replace('_', ' ').title()}"
            else:
                title = phase_titles.get(phase_name, phase_name)

            summary = extract_short_summary(phase_output)
            with st.expander(f"{title} — {summary}", expanded=False):
                st.markdown(phase_output)
                st.caption(f"⏱ {duration:.1f}s • {timestamp}")

        st.divider()

        if loaded_session.get("final_solution"):
            st.markdown("## 🎉 FINALE LÖSUNG")
            with st.container(border=True):
                st.write(loaded_session.get("final_solution"))

            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.download_button(
                    label="📥 Lösung als TXT herunterladen",
                    data=loaded_session.get("final_solution"), # type: ignore
                    file_name="agent_solution.txt",
                    mime="text/plain",
                    use_container_width=True
                )

# FALL 2: Neues Problem
else:
    # Eingabe für Problem mit Formular
    with st.form("problem_form", clear_on_submit=False):
        user_input = st.text_area(
            "🎯 Was ist dein Problem?",
            height=100,
            placeholder="Beschreibe hier dein Problem detailliert... (Ctrl+Enter zum Abschicken)"
        )

        col1, col2, col3 = st.columns([1, 1, 8])
        with col1:
            solve_button = st.form_submit_button("🚀 Lösen", use_container_width=True, type="primary")
        with col2:
            pass
        with col3:
            st.caption("💡 Oder drücke Ctrl+Enter zum Abschicken")

    # Hauptlogik
    if solve_button and user_input:
        st.session_state.problem_result = None

        # Erstelle neue Chat-Session
        chat_session_uuid = storage_manager.create_chat_session(
            user_uuid=st.session_state[SESSION_KEY_USER_ID],
            problem_input=user_input,
            settings={"temperature": user_temperature, "max_refinements": max_refinements}
        )

        # Phase 1: Plan
        with st.spinner("📋 Agent erstellt einen Plan..."):
            start_time = time.time()
            plan = plan_phase(user_input, user_temperature)
            duration = time.time() - start_time

        storage_manager.add_phase_to_session(
            st.session_state[SESSION_KEY_USER_ID],
            chat_session_uuid,
            "planning",
            plan, # type: ignore
            duration_seconds=duration
        )

        plan_summary = extract_short_summary(plan)
        with st.expander(f"📋 Phase 1: Planung — {plan_summary}", expanded=False):
            st.markdown(plan)

        # Phase 2: Ausführung
        with st.spinner("🚀 Agent arbeitet an der Lösung..."):
            start_time = time.time()
            solution = execution_phase(user_input, plan, user_temperature)
            duration = time.time() - start_time

        storage_manager.add_phase_to_session(
            st.session_state[SESSION_KEY_USER_ID],
            chat_session_uuid,
            "execution",
            solution, # type: ignore
            duration_seconds=duration
        )

        solution_summary = extract_short_summary(solution)
        with st.expander(f"🚀 Phase 2: Ausführung — {solution_summary}", expanded=False):
            st.markdown(solution)

        # Refinement Loop
        refinement_count = 0
        while refinement_count < max_refinements:
            # Phase 3: Überprüfung
            with st.spinner("✅ Agent überprüft die Lösung..."):
                start_time = time.time()
                verification, is_acceptable = verification_phase(user_input, plan, solution, user_temperature)
                duration = time.time() - start_time

            storage_manager.add_phase_to_session(
                st.session_state[SESSION_KEY_USER_ID],
                chat_session_uuid,
                "verification",
                verification, # type: ignore
                duration_seconds=duration,
                additional_data={"is_acceptable": is_acceptable}
            )

            verification_summary = extract_short_summary(verification)
            with st.expander(f"✅ Phase 3: Überprüfung — {verification_summary}", expanded=False):
                st.markdown(verification)

            if is_acceptable:
                st.success("🎯 Problem erfolgreich gelöst!")
                st.session_state.problem_result = solution
                storage_manager.complete_chat_session(
                    st.session_state[SESSION_KEY_USER_ID],
                    chat_session_uuid,
                    solution # pyright: ignore[reportArgumentType]
                )
                break
            else:
                refinement_count += 1
                if refinement_count < max_refinements:
                    with st.spinner(f"🔄 Agent verbessert die Lösung (Iteration {refinement_count})..."):
                        start_time = time.time()
                        solution = refinement_phase(
                            user_prompt=user_input,
                            plan=plan,
                            solution=solution,
                            feedback=verification,
                            iteration=refinement_count,
                            user_temperature=user_temperature
                        )
                        duration = time.time() - start_time

                    storage_manager.add_phase_to_session(
                        st.session_state[SESSION_KEY_USER_ID],
                        chat_session_uuid,
                        f"refinement_iteration_{refinement_count}",
                        solution, # type: ignore
                        duration_seconds=duration,
                        additional_data={"feedback": verification}
                    )

                    refinement_summary = extract_short_summary(solution)
                    with st.expander(f"🔄 Phase 4: Verbesserung (Iteration {refinement_count}) — {refinement_summary}", expanded=False):
                        st.markdown(solution)
                else:
                    st.warning(f"⚠️ Max. Iterationen ({max_refinements}) erreicht. Beste Lösung wird akzeptiert.")
                    st.session_state.problem_result = solution
                    storage_manager.complete_chat_session(
                        st.session_state[SESSION_KEY_USER_ID],
                        chat_session_uuid,
                        solution # type: ignore
                    )

    # Finale Lösung anzeigen
    if st.session_state.problem_result:
        st.divider()
        st.markdown("## 🎉 FINALE LÖSUNG")
        st.divider()

        with st.container(border=True):
            st.write(st.session_state.problem_result)

        st.write("")

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.download_button(
                label="📥 Lösung als TXT herunterladen",
                data=st.session_state.problem_result,
                file_name="agent_solution.txt",
                mime="text/plain",
                use_container_width=True
            )
