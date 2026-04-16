import os
import json
import asyncio
import time
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Import local utils
from utils import auth_manager, storage_manager

load_dotenv()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEY is not set in .env")

client = AsyncOpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)
MODEL = "meta/llama-3.1-70b-instruct"

app = FastAPI(title="AI Agent API V2")

# Allow CORS for local frontend testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODELS ===
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class ChatHistoryResponse(BaseModel):
    sessions: List[Dict[str, Any]]

# === AUTH ENDPOINTS ===
@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    success, message = auth_manager.register_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"message": message}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    success, message, user_uuid = auth_manager.login_user(req.username, req.password)
    if not success:
        raise HTTPException(status_code=401, detail=message)
    is_admin = auth_manager.is_admin(user_uuid)
    return {"message": message, "user_id": user_uuid, "username": req.username, "is_admin": is_admin}

# === ADMIN ENDPOINTS ===
@app.get("/api/admin/pending")
async def get_pending(user_id: str):
    if not auth_manager.is_admin(user_id):
        raise HTTPException(status_code=403, detail="Not admin")
    return {"pending_users": auth_manager.get_pending_users()}

@app.post("/api/admin/approve/{pending_uuid}")
async def approve(pending_uuid: str, user_id: str):
    if not auth_manager.is_admin(user_id):
        raise HTTPException(status_code=403, detail="Not admin")
    success, msg = auth_manager.approve_user(pending_uuid)
    return {"success": success, "message": msg}

# === HISTORY ENDPOINTS ===
@app.get("/api/history")
async def get_history(user_id: str):
    # Verify user exists
    if not auth_manager.get_user_info(user_id):
        raise HTTPException(status_code=401, detail="User not found")
    history = storage_manager.get_chat_sessions_summary(user_id)
    return {"sessions": history}

@app.get("/api/history/{session_id}")
async def get_history_detail(session_id: str, user_id: str):
    if not auth_manager.get_user_info(user_id):
        raise HTTPException(status_code=401, detail="User not found")
    session = storage_manager.get_chat_session(user_id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.delete("/api/history/{session_id}")
async def delete_history(session_id: str, user_id: str):
    if not auth_manager.get_user_info(user_id):
        raise HTTPException(status_code=401, detail="User not found")
    success = storage_manager.delete_chat_session(user_id, session_id)
    return {"success": success}

# === WEBSOCKET CHAT AGENT ===
@app.websocket("/api/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    
    # Warte auf Init-Nachricht (user_id, problem_input, settings)
    data = await websocket.receive_text()
    init_data = json.loads(data)
    user_id = init_data.get("user_id")
    problem_input = init_data.get("problem_input")
    settings = init_data.get("settings", {"temperature": 0.7, "max_refinements": 5})
    existing_session_id = init_data.get("session_id")
    
    if not user_id or not problem_input:
        await websocket.send_text(json.dumps({"type": "error", "message": "Missing arguments"}))
        await websocket.close()
        return

    history = ""
    session_id = ""

    if existing_session_id:
        # Continuing an existing session
        session_id = existing_session_id
        session_data = storage_manager.get_chat_session(user_id, session_id)
        if session_data:
            history += f"URSPRÜNGLICHES NUTZER PROBLEM:\n{session_data.get('problem_input', '')}\n"
            for phase in session_data.get('phases', []):
                p_name = phase.get('phase', '')
                p_out = phase.get('output', '')
                if p_name == 'user_followup':
                    history += f"\nNUTZER GIBT NEUE ANWEISUNG:\n{p_out}\n"
                else:
                    history += f"\n[Action: {p_name}] -> Result: {p_out[:200]}...\n"
                    
            history += f"\nNUTZER GIBT NEUE ANWEISUNG:\n{problem_input}\n"
            # Speichere die Nachfrage als Phase ab
            storage_manager.add_phase_to_session(user_id, session_id, "user_followup", problem_input)
            await websocket.send_text(json.dumps({"type": "session_created", "session_id": session_id}))
        else:
            await websocket.send_text(json.dumps({"type": "error", "message": "Session not found"}))
            await websocket.close()
            return
    else:
        # Session in DB ablegen
        session_id = storage_manager.create_chat_session(user_id, problem_input, settings)
        await websocket.send_text(json.dumps({"type": "session_created", "session_id": session_id}))
        history = f"NUTZER PROBLEM:\n{problem_input}\n"

    refinement_count = 0
    max_refinements = settings.get("max_refinements", 5)
    temperature = settings.get("temperature", 0.7)

    # Agent Loop
    while True:
        await websocket.send_text(json.dumps({"type": "status", "message": "Agent denkt nach..."}))
        
        system_prompt = f"""Du bist ein autonomes KI-Gehirn (Master-Orchestrator). Löse das Problem des Nutzers.
Entscheide den NÄCHSTEN logischen Schritt basierend auf dem Problem und Verlauf.
Du hast exakt folgende Werkzeuge (Actions):
1. "DIRECT_ANSWER": Gib sofort eine finale Antwort (Lösung). Verwende dies NICHT für Rückfragen! action_input MUSS die Antwort sein.
2. "ASK_USER": Du brauchst eine Rückmeldung oder hast eine Rückfrage an den Nutzer. action_input MUSS die Frage sein.
3. "SEARCH_WEB": Suche im Internet. action_input = ["begriff1", "begriff2"].
4. "PLAN_EXECUTION": Wenn programmiert oder geplant wird. action_input = [{{"task": "..."}}].
5. "VERIFY": Prüfe den Code/die Lösung auf Fehler. action_input = "Was zu prüfen ist".
6. "FINISH": Lösung ist 100% fertig. action_input = "Die finale Lösung".

Antworte IMMER im JSON-Format wie folgt:
{{
  "thought_process": "...",
  "action": "...",
  "action_input": ...
}}
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Bisheriger Verlauf:\n{history}\n\nEntscheide den nächsten Schritt!"}
        ]

        try:
            start_time = time.time()
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=temperature,
                max_tokens=2048,
            )
            raw_output = response.choices[0].message.content
            duration = time.time() - start_time
            
            # JSON Extraktion
            json_response = None
            try:
                import re
                match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_output, re.DOTALL)
                text_to_parse = match.group(1) if match else raw_output
                json_response = json.loads(text_to_parse)
            except Exception:
                pass

            if not json_response or "action" not in json_response:
                # Fallback directly to text
                await websocket.send_text(json.dumps({
                    "type": "error", 
                    "message": "Agent JSON parse error, retrying..."
                }))
                continue

            action = json_response["action"]
            action_input = json_response.get("action_input")
            thought = json_response.get("thought_process", "")

            # Sende Action an Frontend für UI Notification
            await websocket.send_text(json.dumps({
                "type": "action_started",
                "action": action,
                "thought": thought
            }))

            # ACTION HANDLERS
            action_result = ""
            phase_name = ""

            if action == "DIRECT_ANSWER" or action == "FINISH":
                phase_name = "final_output"
                action_result = str(action_input)
                
            elif action == "ASK_USER":
                phase_name = "ask_user"
                action_result = str(action_input)
                
            elif action == "SEARCH_WEB":
                phase_name = "search"
                from duckduckgo_search import DDGS
                results = []
                with DDGS() as ddgs:
                    for query in (action_input if isinstance(action_input, list) else [action_input]):
                        for r in ddgs.text(query, max_results=3):
                            results.append(f"- {r['title']}: {r['body']}")
                action_result = "\n".join(results)
                
            elif action == "PLAN_EXECUTION":
                phase_name = "execution"
                action_result = f"Führe Tasks aus: {action_input}"
                # Hier würde ein echter Executor greifen
                await asyncio.sleep(2)
                
            elif action == "VERIFY":
                phase_name = "verification"
                action_result = f"Prüfung durchgeführt für: {action_input}"
                await asyncio.sleep(1)

            else:
                phase_name = "unknown"
                action_result = "Unbekannte Aktion."

            # Speichere Phase
            storage_manager.add_phase_to_session(user_id, session_id, phase_name, action_result, duration)
            
            # Informiere UI
            await websocket.send_text(json.dumps({
                "type": "phase_completed",
                "phase": phase_name,
                "result": action_result
            }))

            history += f"\n[Action: {action}] -> Result: {action_result[:200]}...\n"

            if action == "DIRECT_ANSWER" or action == "FINISH":
                storage_manager.complete_chat_session(user_id, session_id, action_result)
                await websocket.send_text(json.dumps({"type": "done", "final_solution": action_result}))
                break
            elif action == "ASK_USER":
                await websocket.send_text(json.dumps({"type": "ask_user", "question": action_result}))
                break

        except Exception as e:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            break
            
    await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
