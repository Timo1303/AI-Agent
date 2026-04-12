import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
import hashlib
import hmac

# ==================== SICHERHEIT ====================
def check_password():
    """Simple Authentifizierung mit Passwort."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.set_page_config(page_title="AI Agent - Login", layout="centered")
        st.title("🔐 AI Agent Login")
        password = st.text_input("Gib dein Passwort ein:", type="password")

        if password:
            # Hier kannst du später ein komplexeres System bauen
            if password == st.secrets.get("APP_PASSWORD", "test123"):
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ Falsches Passwort!")
        return False

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
def query_agent(messages, system_prompt, temperature=0.7, max_tokens=2048):
    """Schickt eine Anfrage an die API."""
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

def plan_phase(user_prompt):
    """Phase 1: Erstellt einen Plan."""
    system_prompt = """Du bist ein intelligenter Agent, der Probleme systematisch löst.
Erstelle einen detaillierten Plan zur Lösung des Problems.

Format:
1. PROBLEM-ANALYSE: Kurze Zusammenfassung
2. LÖSUNGSSCHRITTE: Nummerierte Liste
3. ERFOLGS-KRITERIUM: Woran erkenne ich, dass es gelöst ist?

Sei präzise und strukturiert."""

    messages = [{"role": "user", "content": f"Erstelle einen Plan für: {user_prompt}"}]
    return query_agent(messages, system_prompt)

def execution_phase(user_prompt, plan):
    """Phase 2: Arbeitet den Plan ab."""
    system_prompt = """Du bist ein intelligenter Agent, der Probleme systematisch löst.
Arbeite den Plan Schritt für Schritt ab. Denke laut während du vorgehst.
Erstelle am Ende eine ZUSAMMENFASSUNG der Lösung."""

    messages = [
        {"role": "user", "content": f"""Original-Problem: {user_prompt}

Plan:\n{plan}

Arbeite systematisch an der Lösung."""}
    ]

    return query_agent(messages, system_prompt, max_tokens=3000)

def verification_phase(user_prompt, plan, solution):
    """Phase 3: Überprüft die Lösung."""
    system_prompt = """Du bist ein kritischer Reviewer. Überprüfe die Lösung:

1. ERFÜLLUNG: Wurde das Problem vollständig gelöst?
2. QUALITÄT: Ist die Lösung von guter Qualität?
3. VERBESSERUNGEN: Gibt es noch Verbesserungspotenzial?
4. BEWERTUNG: Note von 1-10
5. FAZIT: Schreibe genau: "FAZIT: ja, ist akzeptabel" oder "FAZIT: nein, nicht akzeptabel"

Sei ehrlich in deiner Bewertung."""

    messages = [
        {"role": "user", "content": f"""Original-Problem: {user_prompt}

Plan: {plan}

Lösung: {solution}

Überprüfe diese Lösung kritisch."""}
    ]

    verification = query_agent(messages, system_prompt, temperature=0.3)
    is_acceptable = extract_acceptance(verification)

    return verification, is_acceptable

def refinement_phase(user_prompt, plan, solution, feedback, iteration):
    """Phase 4: Verbessert die Lösung."""
    system_prompt = """Du bist ein intelligenter Agent, der Feedback annimmt und Lösungen verbessert.
Erstelle eine verbesserte Lösung basierend auf dem Feedback.
Erkläre am Ende, welche Verbesserungen du vorgenommen hast."""

    messages = [
        {"role": "user", "content": f"""Original-Problem: {user_prompt}

Bisherige Lösung: {solution}

Feedback: {feedback}

Erstelle eine verbesserte Lösung."""}
    ]

    return query_agent(messages, system_prompt, max_tokens=3000)

# ==================== STREAMLIT UI ====================
if not check_password():
    st.stop()

st.set_page_config(page_title="🤖 AI Agent", layout="wide", initial_sidebar_state="expanded")

st.title("🤖 AI Agent - Intelligent Problem Solver")
st.markdown("*Powered by NVIDIA NIM & Llama 3.1 70B*")

# Sidebar Konfiguration
with st.sidebar:
    st.header("⚙️ Einstellungen")
    max_refinements = st.slider("Max. Verbesserungsiterationen", 1, 5, 2)
    st.divider()
    st.info("💡 Der Agent wird dein Problem analysieren, einen Plan erstellen, die Lösung entwickeln und dann überprüfen & verbessern!")

# Session State für Verlauf
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "problem_result" not in st.session_state:
    st.session_state.problem_result = None

# Eingabe für Problem
col1, col2 = st.columns([4, 1])
with col1:
    user_input = st.text_area("🎯 Was ist dein Problem?", height=100, placeholder="Beschreibe hier dein Problem detailliert...")

with col2:
    st.write("")
    st.write("")
    solve_button = st.button("🚀 Lösen", use_container_width=True, type="primary")

# Hauptlogik
if solve_button and user_input:
    st.session_state.problem_result = None

    with st.spinner("⏳ Agent arbeitet daran..."):
        # Phase 1: Plan
        st.subheader("📋 Phase 1: Planung")
        plan_placeholder = st.empty()
        with plan_placeholder.container():
            with st.spinner("Der Agent erstellt einen Plan..."):
                plan = plan_phase(user_input)
        plan_placeholder.markdown(f"✅ Plan erstellt\n\n{plan}")

        # Phase 2: Ausführung
        st.subheader("🚀 Phase 2: Ausführung")
        execution_placeholder = st.empty()
        with execution_placeholder.container():
            with st.spinner("Der Agent arbeitet an der Lösung..."):
                solution = execution_phase(user_input, plan)
        execution_placeholder.markdown(f"✅ Lösung entwickelt\n\n{solution}")

        # Refinement Loop
        refinement_count = 0
        while refinement_count < max_refinements:
            # Phase 3: Überprüfung
            st.subheader(f"✅ Phase 3: Überprüfung")
            verification_placeholder = st.empty()
            with verification_placeholder.container():
                with st.spinner("Der Agent überprüft die Lösung..."):
                    verification, is_acceptable = verification_phase(user_input, plan, solution)

            verification_placeholder.markdown(f"{verification}")

            if is_acceptable:
                st.success("🎯 Problem erfolgreich gelöst!")
                st.session_state.problem_result = solution
                break
            else:
                refinement_count += 1
                if refinement_count < max_refinements:
                    st.subheader(f"🔄 Phase 4: Verbesserung (Iteration {refinement_count})")
                    refinement_placeholder = st.empty()
                    with refinement_placeholder.container():
                        with st.spinner("Der Agent verbessert die Lösung..."):
                            solution = refinement_phase(user_input, plan, solution, verification, refinement_count)
                    refinement_placeholder.markdown(f"✅ Lösung verbessert\n\n{solution}")
                else:
                    st.warning(f"⚠️ Max. Iterationen erreicht. Beste Lösung wird akzeptiert.")
                    st.session_state.problem_result = solution

# Finale Lösung anzeigen
if st.session_state.problem_result:
    st.divider()
    st.subheader("🎉 FINALE LÖSUNG")
    with st.container(border=True):
        st.markdown(st.session_state.problem_result)
        # Download Button
        st.download_button(
            label="📥 Lösung als TXT herunterladen",
            data=st.session_state.problem_result,
            file_name="agent_solution.txt",
            mime="text/plain"
        )

# Chat-Verlauf (optional)
if st.session_state.chat_history:
    st.divider()
    st.subheader("📜 Verlauf")
    for msg in st.session_state.chat_history:
        st.write(f"**{msg['role']}:** {msg['content'][:200]}...")
