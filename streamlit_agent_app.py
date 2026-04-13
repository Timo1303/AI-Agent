import streamlit as st
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import sys
import json
import re
import concurrent.futures
from duckduckgo_search import DDGS

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

def extract_json_from_response(text):
    if not text: return None
    try:
        import json
        return json.loads(text)
    except: pass
    try:
        import re
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match: return json.loads(match.group(1))
    except: pass
    try:
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match: return json.loads(match.group(0))
    except: pass
    return None

def controller_agent(user_prompt, history, user_temperature):
    system_prompt = '''Du bist ein autonomes KI-Gehirn (Master-Orchestrator). Löse das Problem des Nutzers.
Entscheide den NÄCHSTEN logischen Schritt basierend auf dem Problem und dem bisherigen Verlauf.
Du hast exakt folgende Werkzeuge (Actions):
1. "DIRECT_ANSWER": Gib sofort eine finale Antwort (für einfache Chat-Fragen, Begrüßungen, simple Erklärungen). action_input MUSS die Antwort als Text sein.
2. "SEARCH_WEB": Suche im Internet (z.B. für Fakten). action_input = ["begriff1", "begriff2"].
3. "PLAN_EXECUTION": Wenn programmiert wird. action_input = [{"task": "Schreibe Backend"}, {"task": "Schreibe Frontend"}]. Dies startet Worker parallel.
4. "VERIFY": Prüfe den Code/die Lösung auf Fehler. action_input = "Was zu prüfen ist".
5. "FINISH": Die Lösung ist 100% fertig, der Nutzer ist zufrieden. action_input = "Die finale Lösung".

Antworte IMMER im JSON-Format, sonst gibt es einen Programmfehler! Beispiel:
{
  "thought_process": "Ich brauche Daten aus dem Internet.",
  "action": "SEARCH_WEB",
  "action_input": ["Wetter 2026", "Lokale News"]
}
'''
    messages = [{"role": "user", "content": f"Problem des Nutzers: {user_prompt}\n\nBisheriger Verlauf aus vorherigen Aktionen:\n{history}\n\nEntscheide den nächsten Schritt!"}]
    return query_agent(messages, system_prompt, user_temperature=user_temperature)

def search_phase(queries):
    results_text = "INTERNET RECHERCHE ERGEBNISSE:\n=========================\n"
    from duckduckgo_search import DDGS
    for query in queries:
        try:
            results = DDGS().text(query, max_results=3)
            results_text += f"\n--- Suche für '{query}' ---\n"
            for r in results:
                results_text += f"Quelle: {r.get('title')}\nURL: {r.get('href')}\nInhalt: {r.get('body')}\n\n"
        except Exception as e:
            results_text += f"\nFehler bei Suche '{query}': {str(e)}\n"
    return results_text

def execution_phase(user_prompt, sub_task, internet_context, user_temperature):
    system_prompt = '''Du bist ein Lösungs-Entwickler-Worker. 
DEINE AUFGABE: Setze diesen Teil des Problems um. Du bist tiefgründig und generierst erstklassigen Code oder Text. Nutz das Internet-Vorwissen, falls relevant!'''
    context_block = f"\nVorwissen (Internet/Verlauf):\n{internet_context}\n" if internet_context else ""
    task_desc = f"Gesamtproblem: {user_prompt}\n\nDeine spezifische Aufgabe:\n{sub_task}"
    messages = [{"role": "user", "content": f"{task_desc}{context_block}\n\nArbeite diese Aufgabe in Vollendung ab."}]
    return query_agent(messages, system_prompt, max_tokens=3000, user_temperature=user_temperature)

def verification_phase(user_prompt, history, user_temperature):
    system_prompt = '''Du bist ein strenger Prüfer. Überprüfe den bisherigen Verlauf critically. Sage, was unvollständig ist.'''
    messages = [{"role": "user", "content": f"Problem: {user_prompt}\nBisher gebaut: {history}\nWas fehlt noch oder ist falsch?"}]
    return query_agent(messages, system_prompt, temperature=0.3, user_temperature=user_temperature)

def assembly_phase(user_prompt, compiled_results, user_temperature):
    system_prompt = '''Integrations-Agent: Kombiniere parallele Bausteine zu einer finalen, sauberen Lösung!'''
    messages = [{"role": "user", "content": f"Problem:\n{user_prompt}\n\nTeilergebnisse:\n{compiled_results}\n\nMache daraus eine perfekte Gesamtlösung."}]
    return query_agent(messages, system_prompt, max_tokens=4000, user_temperature=user_temperature)

# ==================== STREAMLIT UI ====================
auth_check()

st.set_page_config(**PAGE_CONFIG) # type: ignore

st.title("AI Agent - Intelligent Problem Solver")
st.markdown("*Powered by NVIDIA NIM & Llama 3.1 70B*")

# Sidebar mit User-Info
with st.sidebar:
    st.header("⚙️ Einstellungen")

    # User-Info
    admin_suffix = " *(Admin)*" if auth_manager.is_admin(st.session_state[SESSION_KEY_USER_ID]) else ""
    st.info(f"👤 Angemeldet als: **{st.session_state[SESSION_KEY_USERNAME]}**{admin_suffix}")

    if st.button("🚪 Ausloggen", use_container_width=True):
        st.session_state[SESSION_KEY_AUTHENTICATED] = False
        st.session_state[SESSION_KEY_USER_ID] = None
        st.session_state[SESSION_KEY_USERNAME] = None
        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = None
        st.rerun()

    st.divider()

    if st.button("🆕 Neues Problem", type="primary", use_container_width=True):
        st.session_state[SESSION_KEY_CURRENT_CHAT_SESSION] = None
        if "chat_history" in st.session_state:
            del st.session_state["chat_history"]
        if "problem_result" in st.session_state:
            del st.session_state["problem_result"]
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
                            if st.button("✔", help="Genehmigen", key=f"app_{user_uuid}", use_container_width=True):
                                auth_manager.approve_user(user_uuid)
                                st.success("Genehmigt!")
                                st.rerun()
                        with col_rej:
                            if st.button("✖", help="Ablehnen", key=f"rej_{user_uuid}", use_container_width=True):
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
                "planning": "📋 Phase 1: Strategie",
                "search": "🌐 Phase 2: Web-Recherche",
                "parallel_execution": "🚀 Phase 3: Parallele Ausführung",
                "execution": "🚀 Phase 3: Ausführung",
                "assembly": "🧩 Phase 4: Zusammenbau",
                "verification": "✅ Phase 5: Überprüfung",
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

        col1, col2 = st.columns([2, 8])
        with col1:
            solve_button = st.form_submit_button("🚀 Lösen", use_container_width=True, type="primary")

    # Hauptlogik
    if solve_button and user_input:
        st.session_state.problem_result = None

        # Erstelle neue Chat-Session
        chat_session_uuid = storage_manager.create_chat_session(
            user_uuid=st.session_state[SESSION_KEY_USER_ID],
            problem_input=user_input,
            settings={"temperature": user_temperature, "max_refinements": max_refinements}
        )

        # Autonomer Agentic Loop
        st.info("🧠 Autonomer Agent-Modus gestartet...")
        
        history_context = ""
        iteration = 0
        
        while iteration < (max_refinements + 3):
            iteration += 1
            with st.spinner(f"🧩 Agent überlegt (Runde {iteration})..."):
                start_time = time.time()
                controller_resp = controller_agent(user_input, history_context, user_temperature)
                action_json = extract_json_from_response(controller_resp)
                
            if not action_json:
                st.error("JSON Parsing fehlgeschlagen. Der Loop bricht ab.")
                st.session_state.problem_result = "Fehler im Agent-Controller. Roher Text: " + controller_resp
                break
                
            act = action_json.get("action", "UNKNOWN")
            reason = action_json.get("thought_process", "Kein Gedankengang mitgeteilt")
            inp = action_json.get("action_input", "")
            
            with st.expander(f"🔄 Runde {iteration}: {act} — {reason[:60]}...", expanded=False):
                st.write(f"**Gedankengang:** {reason}")
                
                output = ""
                with st.spinner(f"Führe Aktion {act} aus..."):
                    try:
                        if act == "DIRECT_ANSWER":
                            output = str(inp)
                            st.write(output)
                            
                        elif act == "SEARCH_WEB":
                            queries = inp if isinstance(inp, list) else [str(inp)]
                            output = search_phase(queries)
                            st.write(output)
                            
                        elif act == "PLAN_EXECUTION":
                            sub_tasks = inp if isinstance(inp, list) else [{"task": str(inp)}]
                            st.write(f"Starten von {len(sub_tasks)} parallelen Workern...")
                            
                            def run_sub_task(task_obj):
                                task_text = task_obj.get('task', '') if isinstance(task_obj, dict) else str(task_obj)
                                import concurrent.futures
                                return execution_phase(user_input, task_text, history_context, user_temperature)
                                
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(sub_tasks))) as executor:
                                futures = [executor.submit(run_sub_task, t) for t in sub_tasks]
                                for future in concurrent.futures.as_completed(futures):
                                    output += "=== Worker Output ===\n" + future.result() + "\n\n"
                                    
                            # Optional Assembly
                            output = assembly_phase(user_input, output, user_temperature)
                            st.write("Ergebnisse wurden assembliert.")
                            
                        elif act == "VERIFY":
                            output = verification_phase(user_input, history_context, user_temperature)
                            st.write(output)
                            
                        elif act == "FINISH":
                            output = str(inp)
                            st.write("Lösung wurde fertiggestellt!")
                            
                        else:
                            output = f"Unbekannte Aktion ({act}). Breche ab."
                    except Exception as e:
                        output = f"Fehler bei Ausführung ({act}): {str(e)}"
                
                duration = time.time() - start_time
                if not storage_manager.add_phase_to_session(
                    st.session_state[SESSION_KEY_USER_ID], chat_session_uuid,
                    act, output, duration_seconds=duration
                ):
                    pass
                
                history_context += f"\n\n[Aktion beendet: {act}]\n{output}"
                
            if act in ["FINISH", "DIRECT_ANSWER"]:
                st.success("🎯 Mission erfüllt!")
                st.session_state.problem_result = output
                storage_manager.complete_chat_session(
                    st.session_state[SESSION_KEY_USER_ID],
                    chat_session_uuid,
                    output
                )
                break
                
        else:
            st.warning("⚠️ Maximale Denkschleifen erreicht. Beende zwangsweise.")
            st.session_state.problem_result = history_context

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
