-- Supabase Tabellen für den AI Agent (Ausführen im "SQL Editor" auf Supabase)

-- 1. Tabelle für genehmigte Benutzer
CREATE TABLE IF NOT EXISTS users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    status text NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    approved_at timestamp with time zone
);

-- 2. Tabelle für anstehende Registrierungen
CREATE TABLE IF NOT EXISTS pending_approvals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text UNIQUE NOT NULL,
    password_hash text NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Tabelle für Chat-Sessions
CREATE TABLE IF NOT EXISTS chat_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES users(id) ON DELETE CASCADE,
    problem_input text NOT NULL,
    settings jsonb,
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    completed_at timestamp with time zone,
    final_solution text
);

-- 4. Tabelle für einzelne Agent-Phasen
CREATE TABLE IF NOT EXISTS chat_phases (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id uuid REFERENCES chat_sessions(id) ON DELETE CASCADE,
    phase text NOT NULL,
    output text,
    duration_seconds numeric,
    additional_data jsonb,
    timestamp timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ACHTUNG: Die erste Person, die registriert und auf 'admin' gesetzt werden soll.
-- Führe diesen Code NACH deiner ersten Registrierung im Web-Interface aus:
-- UPDATE users SET status = 'admin' WHERE username = 'DeinName';
