"""Chat-Verlauf und Persistierungs-System."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List

from .constants import CHAT_HISTORY_DIR, DATA_DIR


def _ensure_directories():
    """Stelle sicher, dass Verzeichnisse existieren."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHAT_HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _get_user_history_file(user_uuid: str) -> Path:
    """Gebe Pfad zur Chat-History-Datei eines Users."""
    return CHAT_HISTORY_DIR / f"{user_uuid}.json"


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


def create_chat_session(user_uuid: str, problem_input: str, settings: Dict) -> str:
    """
    Erstelle eine neue Chat-Session.

    Args:
        user_uuid: UUID des Benutzers
        problem_input: Die Problembeschreibung
        settings: Dict mit {temperature, max_refinements}

    Returns: chat_session_uuid
    """
    _ensure_directories()

    session_uuid = str(uuid.uuid4())
    history_file = _get_user_history_file(user_uuid)
    history = _load_json(history_file)

    history[session_uuid] = {
        "id": session_uuid,
        "user_uuid": user_uuid,
        "problem_input": problem_input,
        "settings": settings,
        "created_at": _get_timestamp(),
        "phases": [],
        "final_solution": None,
        "completed_at": None
    }

    _save_json(history_file, history)
    return session_uuid


def add_phase_to_session(
    user_uuid: str,
    session_uuid: str,
    phase_name: str,
    output: str,
    duration_seconds: float = 0.0,
    additional_data: Optional[Dict] = None
) -> bool:
    """
    Füge eine Phase zu einer Chat-Session hinzu.

    Args:
        user_uuid: UUID des Benutzers
        session_uuid: UUID der Chat-Session
        phase_name: Name der Phase (z.B. "planning", "execution", "verification", "refinement_iteration_1")
        output: Text-Output dieser Phase
        duration_seconds: Wie lange diese Phase gedauert hat
        additional_data: Zusätzliche Daten (z.B. {"is_acceptable": False, "feedback": "..."})

    Returns: True wenn erfolgreich, False wenn Session nicht existiert
    """
    _ensure_directories()

    history_file = _get_user_history_file(user_uuid)
    history = _load_json(history_file)

    if session_uuid not in history:
        return False

    phase_entry = {
        "phase": phase_name,
        "output": output,
        "timestamp": _get_timestamp(),
        "duration_seconds": duration_seconds
    }

    if additional_data:
        phase_entry.update(additional_data)

    history[session_uuid]["phases"].append(phase_entry)
    _save_json(history_file, history)

    return True


def complete_chat_session(user_uuid: str, session_uuid: str, final_solution: str) -> bool:
    """
    Markiere eine Chat-Session als abgeschlossen.

    Args:
        user_uuid: UUID des Benutzers
        session_uuid: UUID der Chat-Session
        final_solution: Die finale Lösung

    Returns: True wenn erfolgreich, False wenn Session nicht existiert
    """
    _ensure_directories()

    history_file = _get_user_history_file(user_uuid)
    history = _load_json(history_file)

    if session_uuid not in history:
        return False

    history[session_uuid]["final_solution"] = final_solution
    history[session_uuid]["completed_at"] = _get_timestamp()

    _save_json(history_file, history)
    return True


def get_user_chat_history(user_uuid: str) -> Dict:
    """
    Hole kompletten Chat-Verlauf eines Benutzers.

    Returns: Dict von all seinen Chat-Sessions
    """
    _ensure_directories()

    history_file = _get_user_history_file(user_uuid)
    return _load_json(history_file)


def get_chat_session(user_uuid: str, session_uuid: str) -> Optional[Dict]:
    """
    Hole eine einzelne Chat-Session.

    Returns: Session-Dict oder None wenn nicht existiert
    """
    _ensure_directories()

    history_file = _get_user_history_file(user_uuid)
    history = _load_json(history_file)

    return history.get(session_uuid)


def get_chat_sessions_summary(user_uuid: str) -> List[Dict]:
    """
    Hole Kurzzusammenfassung aller Chat-Sessions eines Benutzers für die UI.

    Returns: Liste von {id, created_at, problem_input_short, phases_count, completed}
    """
    _ensure_directories()

    history = get_user_chat_history(user_uuid)
    summary = []

    for session_uuid, session in sorted(history.items(), reverse=True):
        problem_short = session.get("problem_input", "")[:100]
        if len(session.get("problem_input", "")) > 100:
            problem_short += "..."

        summary.append({
            "id": session_uuid,
            "created_at": session.get("created_at", ""),
            "problem_input_short": problem_short,
            "phases_count": len(session.get("phases", [])),
            "completed": session.get("completed_at") is not None
        })

    return summary


def delete_chat_session(user_uuid: str, session_uuid: str) -> bool:
    """
    Lösche eine Chat-Session.

    Returns: True wenn erfolgreich, False wenn Session nicht existiert
    """
    _ensure_directories()

    history_file = _get_user_history_file(user_uuid)
    history = _load_json(history_file)

    if session_uuid not in history:
        return False

    del history[session_uuid]
    _save_json(history_file, history)

    return True
