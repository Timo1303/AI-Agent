import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI

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
def query_agent(messages, system_prompt, temperature=0.7, max_tokens=2048, user_temperature=None):
    """Schickt eine Anfrage an die API."""
    # Nutze user_temperature wenn von User überschrieben
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

def extract_summary(text, max_lines=3):
    """Extrahiert eine kurze Zusammenfassung aus Text."""
    lines = text.split('\n')
    summary = '\n'.join(lines[:max_lines])
    if len(lines) > max_lines:
        summary += "\n... (mehr Details)"
    return summary

def plan_phase(user_prompt, user_temperature):
    """Phase 1: Erstellt einen Plan."""
    system_prompt = """Du bist ein intelligenter Agent, der Probleme systematisch löst.
Erstelle einen detaillierten Plan zur Lösung des Problems.

Format:
1. PROBLEM-ANALYSE: Kurze Zusammenfassung
2. LÖSUNGSSCHRITTE: Nummerierte Liste
3. ERFOLGS-KRITERIUM: Woran erkenne ich, dass es gelöst ist?

Sei präzise und strukturiert."""

    messages = [{"role": "user", "content": f"Erstelle einen Plan für: {user_prompt}"}]
    return query_agent(messages, system_prompt, user_temperature=user_temperature)

def execution_phase(user_prompt, plan, user_temperature):
    """Phase 2: Arbeitet den Plan ab."""
    system_prompt = """Du bist ein intelligenter Agent, der Probleme systematisch löst.
Arbeite den Plan Schritt für Schritt ab. Denke laut während du vorgehst.
Erstelle am Ende eine ZUSAMMENFASSUNG der Lösung."""

    messages = [
        {"role": "user", "content": f"""Original-Problem: {user_prompt}

Plan:\n{plan}

Arbeite systematisch an der Lösung."""}
    ]

    return query_agent(messages, system_prompt, max_tokens=3000, user_temperature=user_temperature)

def verification_phase(user_prompt, plan, solution, user_temperature):
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

    verification = query_agent(messages, system_prompt, temperature=0.3, user_temperature=user_temperature)
    is_acceptable = extract_acceptance(verification)

    return verification, is_acceptable

def refinement_phase(user_prompt, plan, solution, feedback, iteration, user_temperature):
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

    return query_agent(messages, system_prompt, max_tokens=3000, user_temperature=user_temperature)

# ==================== STREAMLIT UI ====================
if not check_password():
    st.stop()

st.set_page_config(page_title="🤖 AI Agent", layout="wide", initial_sidebar_state="expanded")

st.title("🤖 AI Agent - Intelligent Problem Solver")
st.markdown("*Powered by NVIDIA NIM & Llama 3.1 70B*")

# Sidebar Konfiguration
with st.sidebar:
    st.header("⚙️ Einstellungen")
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

    # Phase 1: Plan
    with st.expander("📋 Phase 1: Planung", expanded=True):
        with st.spinner("Der Agent erstellt einen Plan..."):
            plan = plan_phase(user_input, user_temperature)
            if plan:
                summary = extract_summary(plan)
                st.markdown(f"**Zusammenfassung:**\n{summary}")

    # Phase 2: Ausführung
    with st.expander("🚀 Phase 2: Ausführung", expanded=True):
        with st.spinner("Der Agent arbeitet an der Lösung..."):
            solution = execution_phase(user_input, plan, user_temperature)
            if solution:
                summary = extract_summary(solution)
                st.markdown(f"**Zusammenfassung:**\n{summary}")

    # Refinement Loop
    refinement_count = 0
    while refinement_count < max_refinements:
        # Phase 3: Überprüfung
        with st.expander(f"✅ Phase 3: Überprüfung", expanded=True):
            with st.spinner("Der Agent überprüft die Lösung..."):
                verification, is_acceptable = verification_phase(user_input, plan, solution, user_temperature)

                if verification:
                    summary = extract_summary(verification)
                    st.markdown(f"**Bewertung:**\n{summary}")

        if is_acceptable:
            st.success("🎯 Problem erfolgreich gelöst!")
            st.session_state.problem_result = solution
            break
        else:
            refinement_count += 1
            if refinement_count < max_refinements:
                with st.expander(f"🔄 Phase 4: Verbesserung (Iteration {refinement_count})", expanded=True):
                    with st.spinner("Der Agent verbessert die Lösung..."):
                        solution = refinement_phase(user_prompt=user_input, plan=plan, solution=solution,
                                                   feedback=verification, iteration=refinement_count,
                                                   user_temperature=user_temperature)
                        if solution:
                            summary = extract_summary(solution)
                            st.markdown(f"**Zusammenfassung der Verbesserungen:**\n{summary}")
            else:
                st.warning(f"⚠️ Max. Iterationen ({max_refinements}) erreicht. Beste Lösung wird akzeptiert.")
                st.session_state.problem_result = solution

# Finale Lösung anzeigen (GROSS und deutlich)
if st.session_state.problem_result:
    st.divider()
    st.markdown("---")
    st.markdown("## 🎉 FINALE LÖSUNG")
    st.markdown("---")

    with st.container(border=True):
        col1, col2 = st.columns([1, 4])
        with col1:
            st.markdown("### ✅")
        with col2:
            st.markdown("### Die optimierte Lösung:")

    # Große, gut lesbare Ausgabe
    st.markdown(f"""
    <div style="background-color: #f0f8ff; padding: 30px; border-radius: 10px; border-left: 5px solid #0066cc;">

    {st.session_state.problem_result}

    </div>
    """, unsafe_allow_html=True)

    # Download Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label="📥 Lösung als TXT herunterladen",
            data=st.session_state.problem_result,
            file_name="agent_solution.txt",
            mime="text/plain",
            use_container_width=True
        )
