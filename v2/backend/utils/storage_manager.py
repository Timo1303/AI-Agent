"""Chat-Verlauf und Persistierungs-System (Supabase Edition)."""
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List
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

def _get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def create_chat_session(user_uuid: str, problem_input: str, settings: Dict) -> str:
    if not supabase: return "no-db"
    res = supabase.table("chat_sessions").insert({
        "user_id": user_uuid,
        "problem_input": problem_input,
        "settings": settings
    }).execute()
    return res.data[0]["id"]

def add_phase_to_session(user_uuid: str, session_uuid: str, phase_name: str, output: str, duration_seconds: float = 0.0, additional_data: Optional[Dict] = None) -> bool:
    if not supabase or session_uuid == "no-db": return False
    supabase.table("chat_phases").insert({
        "session_id": session_uuid,
        "phase": phase_name,
        "output": output,
        "duration_seconds": duration_seconds,
        "additional_data": additional_data or {}
    }).execute()
    return True

def complete_chat_session(user_uuid: str, session_uuid: str, final_solution: str) -> bool:
    if not supabase or session_uuid == "no-db": return False
    supabase.table("chat_sessions").update({
        "final_solution": final_solution,
        "completed_at": _get_timestamp()
    }).eq("id", session_uuid).execute()
    return True

def get_user_chat_history(user_uuid: str) -> Dict:
    if not supabase: return {}
    res = supabase.table("chat_sessions").select("*, chat_phases(*)").eq("user_id", user_uuid).order("created_at", desc=True).execute()
    history = {}
    for session in res.data:
        phases = session.pop("chat_phases", [])
        phases = sorted(phases, key=lambda x: x["timestamp"])
        session["phases"] = phases
        history[session["id"]] = session
    return history

def get_chat_session(user_uuid: str, session_uuid: str) -> Optional[Dict]:
    history = get_user_chat_history(user_uuid)
    return history.get(session_uuid)

def get_chat_sessions_summary(user_uuid: str) -> List[Dict]:
    history = get_user_chat_history(user_uuid)
    summary = []
    for session_uuid, session in history.items():
        problem_short = session.get("problem_input", "")[:100]
        if len(session.get("problem_input", "")) > 100: problem_short += "..."

        summary.append({
            "id": session_uuid,
            "created_at": session.get("created_at", ""),
            "problem_input_short": problem_short,
            "phases_count": len(session.get("phases", [])),
            "completed": session.get("completed_at") is not None
        })
    return summary

def delete_chat_session(user_uuid: str, session_uuid: str) -> bool:
    if not supabase or session_uuid == "no-db": return False
    supabase.table("chat_sessions").delete().eq("id", session_uuid).execute()
    return True
