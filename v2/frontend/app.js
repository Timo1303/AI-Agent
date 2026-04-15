// ==========================================
// EINSTELLUNGEN:
// Wenn du die App auf Render hochlädst, trage hier die URL ein:
const RENDER_DOMAIN = 'ai-agent-jfmf.onrender.com';
// ==========================================

const isProd = window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1';
const API_URL = isProd ? `https://${RENDER_DOMAIN}/api` : 'http://127.0.0.1:8000/api';
const WS_URL = isProd ? `wss://${RENDER_DOMAIN}/api/ws/chat` : 'ws://127.0.0.1:8000/api/ws/chat';

let currentUser = null;
let currentSocket = null;

// Auth UI Logic
function switchAuthTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    document.getElementById('login-form').style.display = tab === 'login' ? 'block' : 'none';
    document.getElementById('register-form').style.display = tab === 'register' ? 'block' : 'none';
    document.getElementById('auth-message').innerText = '';
}

function showMessage(msg, isError = false) {
    const el = document.getElementById('auth-message');
    el.innerText = msg;
    el.style.color = isError ? '#ef4444' : '#4ade80';
}

// API Calls
async function login() {
    const u = document.getElementById('login-username').value;
    const p = document.getElementById('login-password').value;
    try {
        const res = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);

        currentUser = data;
        initApp();
    } catch (e) {
        showMessage(e.message, true);
    }
}

async function register() {
    const u = document.getElementById('reg-username').value;
    const p = document.getElementById('reg-password').value;
    try {
        const res = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: u, password: p })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail);
        showMessage(data.message);
    } catch (e) {
        showMessage(e.message, true);
    }
}

function logout() {
    currentUser = null;
    document.getElementById('main-screen').classList.remove('active');
    setTimeout(() => {
        document.getElementById('main-screen').classList.add('hidden');
        document.getElementById('auth-screen').classList.remove('hidden');
        setTimeout(() => document.getElementById('auth-screen').classList.add('active'), 50);
    }, 500);
}

// Main App Logic
function initApp() {
    document.getElementById('auth-screen').classList.remove('active');
    setTimeout(() => {
        document.getElementById('auth-screen').classList.add('hidden');
        document.getElementById('main-screen').classList.remove('hidden');
        setTimeout(() => document.getElementById('main-screen').classList.add('active'), 50);
    }, 500);

    document.getElementById('display-username').innerText = currentUser.username;

    if (currentUser.is_admin) {
        document.getElementById('role-badge').innerText = 'Admin';
        document.getElementById('role-badge').style.color = '#f59e0b';
        document.getElementById('admin-nav-btn').style.display = 'flex';
        loadAdminPanel();
    } else {
        document.getElementById('role-badge').innerText = 'User';
        document.getElementById('role-badge').style.color = 'var(--text-muted)';
        document.getElementById('admin-nav-btn').style.display = 'none';
    }
}

function showView(viewId) {
    document.querySelectorAll('.view-content').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById(`view-${viewId}`).classList.add('active');
    event.currentTarget.classList.add('active');

    if(viewId === 'history') {
        loadHistory();
    }
}

// History Logic
async function loadHistory() {
    try {
        const res = await fetch(`${API_URL}/history?user_id=${currentUser.user_id}`);
        const data = await res.json();
        const list = document.getElementById('history-list'); // Assumes we add this to index.html
        if (!list) return; // If missing in DOM, ignore
        list.innerHTML = '';
        
        if(!data.sessions || data.sessions.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted); text-align:center; padding: 20px;">Noch kein Verlauf vorhanden</div>';
            return;
        }

        data.sessions.forEach(session => {
            const card = document.createElement('div');
            card.className = 'user-card';
            card.innerHTML = `
                <div>
                    <h4 style="margin-bottom: 5px;">Problem: ${session.problem_input_short.substring(0, 50)}...</h4>
                    <span style="font-size:0.8rem; color:var(--text-muted); margin-right: 15px;">📅 ${session.created_at.substring(0, 10)}</span>
                    <span style="font-size:0.8rem; color:var(--text-muted)">🔄 ${session.phases_count} Schritte</span>
                </div>
                <div class="user-card-actions">
                    <button class="btn-reject" onclick="deleteHistory('${session.id}')">🗑️</button>
                </div>
            `;
            list.appendChild(card);
        });
    } catch(e) {
        console.error("Load History Error:", e);
    }
}

async function deleteHistory(sessionId) {
    await fetch(`${API_URL}/history/${sessionId}?user_id=${currentUser.user_id}`, { method: 'DELETE' });
    loadHistory();
}

// Admin Logic
async function loadAdminPanel() {
    if (!currentUser?.is_admin) return;
    try {
        const res = await fetch(`${API_URL}/admin/pending?user_id=${currentUser.user_id}`);
        const data = await res.json();

        const list = document.getElementById('pending-list');
        list.innerHTML = '';

        if (Object.keys(data.pending_users).length === 0) {
            list.innerHTML = '<div class="user-card" style="justify-content:center; color: var(--text-muted)">✅ Keine Warteraum-Einträge</div>';
            return;
        }

        for (const [uuid, user] of Object.entries(data.pending_users)) {
            const card = document.createElement('div');
            card.className = 'user-card';
            card.innerHTML = `
                <div>
                    <h4>${user.username}</h4>
                    <span style="font-size:0.8rem; color:var(--text-muted)">${user.created_at.substring(0, 10)}</span>
                </div>
                <div class="user-card-actions">
                    <button class="btn-approve" onclick="approveUser('${uuid}')">✔</button>
                    <button class="btn-reject" onclick="rejectUser('${uuid}')">✖</button>
                </div>
            `;
            list.appendChild(card);
        }
    } catch (e) {
        console.error("Admin Load Error", e);
    }
}

async function approveUser(uuid) {
    await fetch(`${API_URL}/admin/approve/${uuid}?user_id=${currentUser.user_id}`, { method: 'POST' });
    loadAdminPanel();
}

// Agent WebSocket Logic
let currentLoader = null;

function removeLoader() {
    if(currentLoader && currentLoader.parentNode) {
        currentLoader.parentNode.removeChild(currentLoader);
    }
    currentLoader = null;
}

function showLoader(stream) {
    removeLoader();
    currentLoader = document.createElement('div');
    currentLoader.className = 'msg-row msg-agent';
    currentLoader.innerHTML = `
        <div class="agent-message">
            <div class="loader-dots"><div></div><div></div><div></div></div>
        </div>
    `;
    stream.appendChild(currentLoader);
    stream.scrollTop = stream.scrollHeight;
}

function startAgent() {
    const input = document.getElementById('problem-input').value;
    if (!input) return;

    document.getElementById('problem-input').value = '';

    const stream = document.getElementById('chat-stream');
    stream.innerHTML = `
        <div class="msg-row msg-user">
            <div class="user-msg">${input}</div>
        </div>
    `;

    if (currentSocket) currentSocket.close();

    currentSocket = new WebSocket(WS_URL);

    currentSocket.onopen = () => {
        currentSocket.send(JSON.stringify({
            user_id: currentUser.user_id,
            problem_input: input,
            settings: {}
        }));
        showLoader(stream);
    };

    currentSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);
        
        if(data.type === 'status') {
            showLoader(stream);
            return;
        }

        removeLoader();

        const row = document.createElement('div');
        row.className = 'msg-row msg-agent';
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'agent-message';

        if (data.type === 'action_started') {
            msgDiv.innerHTML = `
                <div class="agent-action">⚙️ ${data.action}</div>
                <div class="agent-thought">🧠 ${data.thought}</div>
            `;
            row.appendChild(msgDiv);
            stream.appendChild(row);
        } else if (data.type === 'phase_completed') {
            msgDiv.innerHTML = `<p>${data.result.replace(/\\n/g, '<br>')}</p>`;
            row.appendChild(msgDiv);
            stream.appendChild(row);
        } else if (data.type === 'done') {
            msgDiv.className = 'agent-message final-msg';
            msgDiv.style.borderLeft = '4px solid #4ade80';
            msgDiv.innerHTML = `<h3>✅ Finale Lösung:</h3><p>${data.final_solution.replace(/\\n/g, '<br>')}</p>`;
            row.appendChild(msgDiv);
            stream.appendChild(row);
        } else if (data.type === 'error') {
            msgDiv.className = 'agent-message error-msg';
            msgDiv.style.borderLeft = '4px solid #ef4444';
            msgDiv.innerHTML = `<h3>❌ Fehler:</h3><p>${data.message}</p>`;
            row.appendChild(msgDiv);
            stream.appendChild(row);
        }

        stream.scrollTop = stream.scrollHeight;
        if(data.type !== 'done' && data.type !== 'error') {
            showLoader(stream); // Put loader back until done
        }
    };
}
