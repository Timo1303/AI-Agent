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

def extract_short_summary(text, max_chars=150):
    """Extrahiert eine sehr kurze Zusammenfassung für den Expander-Title."""
    if not text:
        return "Verarbeitet..."

    # Entferne Markdown und nimm erste 150 Zeichen
    lines = text.split('\n')
    summary = ' '.join(lines)

    # Entferne Markdown-Symbole
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
if not check_password():
    st.stop()

st.set_page_config(page_title="AI Agent", layout="wide", initial_sidebar_state="expanded")

st.title("AI Agent - Intelligent Problem Solver")
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

# Eingabe für Problem mit Formular (unterstützt Ctrl+Enter)
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

    # Phase 1: Plan
    with st.spinner("📋 Agent erstellt einen Plan..."):
        plan = plan_phase(user_input, user_temperature)

    plan_summary = extract_short_summary(plan)
    with st.expander(f"📋 Phase 1: Planung — {plan_summary}", expanded=False):
        st.markdown(plan)

    # Phase 2: Ausführung
    with st.spinner("🚀 Agent arbeitet an der Lösung..."):
        solution = execution_phase(user_input, plan, user_temperature)

    solution_summary = extract_short_summary(solution)
    with st.expander(f"🚀 Phase 2: Ausführung — {solution_summary}", expanded=False):
        st.markdown(solution)

    # Refinement Loop
    refinement_count = 0
    while refinement_count < max_refinements:
        # Phase 3: Überprüfung
        with st.spinner("✅ Agent überprüft die Lösung..."):
            verification, is_acceptable = verification_phase(user_input, plan, solution, user_temperature)

        verification_summary = extract_short_summary(verification)
        with st.expander(f"✅ Phase 3: Überprüfung — {verification_summary}", expanded=False):
            st.markdown(verification)

        if is_acceptable:
            st.success("🎯 Problem erfolgreich gelöst!")
            st.session_state.problem_result = solution
            break
        else:
            refinement_count += 1
            if refinement_count < max_refinements:
                with st.spinner(f"🔄 Agent verbessert die Lösung (Iteration {refinement_count})..."):
                    solution = refinement_phase(
                        user_prompt=user_input,
                        plan=plan,
                        solution=solution,
                        feedback=verification,
                        iteration=refinement_count,
                        user_temperature=user_temperature
                    )

                refinement_summary = extract_short_summary(solution)
                with st.expander(f"🔄 Phase 4: Verbesserung (Iteration {refinement_count}) — {refinement_summary}", expanded=False):
                    st.markdown(solution)
            else:
                st.warning(f"⚠️ Max. Iterationen ({max_refinements}) erreicht. Beste Lösung wird akzeptiert.")
                st.session_state.problem_result = solution

# Finale Lösung anzeigen (GROSS und deutlich)
if st.session_state.problem_result:
    st.divider()
    st.markdown("---")
    st.markdown("## 🎉 FINALE LÖSUNG")
    st.markdown("---")

    # Große, gut lesbare Ausgabe mit korrekter Formatierung
    st.markdown(f"""
    <div style="
        background-color: #f0f8ff;
        padding: 25px;
        border-radius: 8px;
        border-left: 4px solid #0066cc;
        font-size: 15px;
        line-height: 1.7;
        white-space: pre-line;
        word-break: break-word;
        color: #333333;
        font-family: 'Courier New', monospace;
        overflow-x: auto;
    ">
{st.session_state.problem_result.replace('<', '&lt;').replace('>', '&gt;')}
    </div>
    """, unsafe_allow_html=True)

    st.write("")  # Spacing

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
