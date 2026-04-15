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
function startAgent() {
    const input = document.getElementById('problem-input').value;
    if (!input) return;

    document.getElementById('problem-input').value = '';

    const stream = document.getElementById('chat-stream');
    stream.innerHTML = `
        <div class="agent-message user-msg">
            <p><strong>Du:</strong> ${input}</p>
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
    };

    currentSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data);

        const msgDiv = document.createElement('div');
        msgDiv.className = 'agent-message';

        if (data.type === 'action_started') {
            msgDiv.innerHTML = `
                <div class="agent-action">⚙️ ${data.action}</div>
                <div class="agent-thought">🧠 ${data.thought}</div>
            `;
            stream.appendChild(msgDiv);
        } else if (data.type === 'phase_completed') {
            msgDiv.innerHTML = `<p>${data.result.replace(/\\n/g, '<br>')}</p>`;
            stream.appendChild(msgDiv);
        } else if (data.type === 'done') {
            const finalDiv = document.createElement('div');
            finalDiv.className = 'agent-message final-msg';
            finalDiv.style.borderLeft = '4px solid #4ade80';
            finalDiv.innerHTML = `<h3>✅ Finale Lösung:</h3><p>${data.final_solution.replace(/\\n/g, '<br>')}</p>`;
            stream.appendChild(finalDiv);
        } else if (data.type === 'error') {
            const errDiv = document.createElement('div');
            errDiv.className = 'agent-message error-msg';
            errDiv.style.borderLeft = '4px solid #ef4444';
            errDiv.innerHTML = `<h3>❌ Fehler:</h3><p>${data.message}</p>`;
            stream.appendChild(errDiv);
        }

        stream.scrollTop = stream.scrollHeight;
    };
}
