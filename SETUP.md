# AI Agent - Neue Features: Multi-User & Chat-Historie

Die App wurde erfolgreich zu einem **Multi-User Account-System** mit **persistenter Chat-Historie** aktualisiert! 🎉

## Was ist neu?

### 1. **Account-System mit Admin-Genehmigung**
- Nutzer können sich selbst registrieren
- Neue Accounts warten auf deine (Admin) Genehmigung
- Nach Genehmigung können sie sich mit Username + Passwort einloggen
- Passwörter werden sicher mit PBKDF2-Hashing gespeichert

### 2. **Persistente Chat-Historie**
- Jeder Chat wird automatisch gespeichert
- Alle Phasen werden dokumentiert: Planung, Ausführung, Verifikation, Verbesserungen
- Metadaten: Zeitstempel, Dauer, Temperatur-Einstellungen
- Chats können später geladen und erneut angesehen werden

### 3. **Admin-Panel**
- Separate Admin-Seite zur Verwaltung von Benutzern
- Genehmigen/Ablehnen von neuen Registrierungsanfragen
- Übersicht aller Benutzer
- Benutzer löschen (wenn nötig)

---

## Wie man die App startet

### Hauptapp (Nutzer)
```bash
streamlit run streamlit_agent_app.py
```

### Admin-Panel (du)
```bash
streamlit run admin_panel.py
```

> **Tipp:** Du kannst beide gleichzeitig in verschiedenen Terminal-Fenster laufen lassen.

---

## Workflow: Schritt-für-Schritt

### Für neue Nutzer:
1. **Öffne die Hauptapp** (`streamlit run streamlit_agent_app.py`)
2. **Wähle "📝 Registrierung"** 
3. **Gib ein:** Username, Email, Passwort
4. **Warte auf Genehmigung** (du wirst benachrichtigt)

### Für dich (Admin):
1. **Öffne das Admin-Panel** (`streamlit run admin_panel.py`)
2. **Login mit deinem Admin-Passwort** (gleich wie vorher)
3. **Prüfe "⏳ Ausstehende Genehmigungen"**
4. **Klick "✅ Genehmigen"** für den neuen User

### Für genehmigte Nutzer:
1. **Login** mit Username + Passwort
2. **Löse dein Problem** mit dem Agent (wie gewohnt)
3. **Chat wird automatisch gespeichert**
4. **Sidebar: "📋 Chat-Verlauf"** - Lade alte Chats jederzeit

---

## Technische Details

### Neue Dateien
```
utils/
├── constants.py         # Konfiguration & Pfade
├── auth_manager.py      # User-Verwaltung
├── storage_manager.py   # Chat-Persistierung
└── __init__.py

admin_panel.py           # Admin-Interface
data/
├── users.json           # Genehmigte Benutzer
├── pending_approvals.json # Registrierungsanfragen in Bearbeitung
└── chat_history/
    ├── user_uuid_1.json # Chats von Nutzer 1
    ├── user_uuid_2.json # Chats von Nutzer 2
    └── ...
```

### Datenspeicherung
- **Benutzer:** JSON-Dateien (einfach, wartbar)
- **Passwörter:** PBKDF2-Hashing (sicher)
- **Chat-Historie:** Vollständige Dokumentation aller Phasen
- **Skalierbarkeit:** Sollte für <1000 Nutzer gut funktionieren

---

## Sicherheit

✅ **Passwort-Hashing:** PBKDF2 mit 100.000 Iterationen
✅ **Admin-Gatekeeper:** Nur von dir genehmigte Nutzer können sich einloggen
✅ **Session-basiert:** Automatisches Logout bei Browser-Refresh
✅ **JSON-Speicher:** Sensible Daten lokal, keine externen Services

---

## Häufig gestellte Fragen

**F: Können Nutzer ihre Passwörter ändern?**
A: Aktuell nicht in der UI. Du kannst das in `admin_panel.py` als Erweiterung hinzufügen.

**F: Wie lange werden Chats gespeichert?**
A: Unbegrenzt. Du kannst alte Chats über das Admin-Panel löschen, wenn nötig.

**F: Was wenn ich einen Nutzer löschen möchte?**
A: Gehe zu "👥 Alle Benutzer" im Admin-Panel → Klick "🗑 Löschen"

**F: Kann ich die JSON-Dateien direkt bearbeiten?**
A: Ja, aber Vorsicht: Fehler können die Struktur beschädigen. Am besten über die UI verwalten.

---

## Nächste Schritte (Optional)

Falls du später Verbesserungen möchtest:
- **Passwort-Reset:** Nutzer können ihr Passwort zurücksetzen
- **Export:** Chats als PDF/Markdown exportieren
- **Statistik:** Detaillierte Nutzer-Aktivität tracken  
- **PostgreSQL:** Upgrade zu echter Datenbank für Skalierbarkeit

---

## Problembehebung

**Error: `ModuleNotFoundError`**
- Stelle sicher, dass `utils/__init__.py` existiert
- Starte die App aus dem `ai-agent`-Verzeichnis

**Passwort-Login schlägt fehl**
- Überprüfe, dass das Admin-Passwort korrekt gestellt in secrets ist
- Test: `streamlit secrets show` sollte `APP_PASSWORD` anzeigen

**Alte Chats werden nicht geladen**
- Die Chat-Dateien sind unter `data/chat_history/` gespeichert
- Überprüfe, dass die User-UUID korrekt ist

---

**Viel Spaß mit der neuen Version!** 🚀
