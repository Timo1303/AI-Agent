# 🤖 AI Agent - Intelligent Problem Solver

> Ein intelligenter KI-Agent, der Probleme **systematisch analysiert, plant, löst und optimiert**. Powered by **NVIDIA NIM** & **Llama 3.1 70B**.

---

## ✨ Features

### 🧠 Intelligenter Workflow
- **📋 Phase 1: Planung** - Der Agent erstellt einen detaillierten Lösungsplan
- **🚀 Phase 2: Ausführung** - Systematische Umsetzung des Plans
- **✅ Phase 3: Überprüfung** - Kritische Bewertung der Lösung (0-10 Punkte)
- **🔄 Phase 4: Verbesserung** - Iterative Optimierung bei Bedarf

### 🎮 Benutzerfreundliche Bedienung
- 🔐 **Passwort-geschützt** - Sichere Authentifizierung
- 📱 **Responsive Design** - Funktioniert auf Handy, Tablet & Desktop
- ⚙️ **Einstellbar** - Temperatur & Verbesserungsiterationen anpassbar
- 💾 **Exportierbar** - Lösungen als TXT herunterladen

### 🔒 Sichere API-Integration
- ✅ API-Keys in **Secrets** (nicht im Code!)
- ✅ `.gitignore` schützt sensible Daten
- ✅ Umgebungsvariablen für sichere Konfiguration

---

## 🚀 Schneller Start

### Voraussetzungen
- Python 3.8+
- NVIDIA NIM API Key ([hier kostenlos bekommen](https://build.nvidia.com/meta/llama-3-1-70b-instruct))
- Git & GitHub Account

### 1️⃣ Repository klonen
```bash
git clone https://github.com/yourusername/ai-agent.git
cd ai-agent
```

### 2️⃣ Dependencies installieren
```bash
pip install -r requirements.txt
```

### 3️⃣ Lokale .env erstellen
```bash
echo "NVIDIA_API_KEY=your-api-key-here" > .env
echo "APP_PASSWORD=your-password-here" >> .env
```

### 4️⃣ App starten
```bash
streamlit run streamlit_agent_app.py
```

Die App läuft dann auf `http://localhost:8501` 🎉

---

## ☁️ Deployment auf Streamlit Cloud

### 1. GitHub Integration
```
1. Repository auf GitHub pushen
2. Streamlit Cloud: https://share.streamlit.io/new
3. Repository wählen
4. Main File: streamlit_agent_app.py
```

### 2. Secrets konfigurieren
```
1. App Settings → Secrets
2. Einfügen:

NVIDIA_API_KEY = "your-api-key"
APP_PASSWORD = "your-password"
```

Deine App ist jetzt **24/7 online** und überall erreichbar! 🌐

---

## 💡 Verwendungsbeispiele

### Beispiel 1: Reiseplanung
```
Input: "Plane einen 2-Tage-Trip nach München, gehe davon aus, 
        dass ich in Nürnberg wohne und Kultur interessiert mich"

Output: 
1. Plan mit Sehenswürdigkeiten & Zeitplan
2. Detaillierter Reiseablauf
3. Überprüfung auf Vollständigkeit
4. Optional: Verbesserungen
```

### Beispiel 2: Problembewältigung
```
Input: "Ich habe Probleme mit Anxiety. 
        Gib mir Strategien und einen Aktionsplan."

Output:
1. Plan zur strukturierten Angstbewältigung
2. Konkrete Strategien & Techniken
3. Bewertung der Lösung
4. Optimierte Version mit Feedback
```

---

## ⚙️ Konfiguration

### Sidebar-Einstellungen

| Einstellung | Bereich | Default | Beschreibung |
|-------------|---------|---------|------------|
| **Max. Verbesserungsiterationen** | 1-10 | 5 | Wie oft der Agent opti­miert |
| **Temperatur (Kreativität)** | 0.0-1.0 | 0.7 | 0.0 = präzise, 1.0 = kreativ |

---

## 📁 Projektstruktur

```
ai-agent/
├── streamlit_agent_app.py      # Hauptanwendung
├── requirements.txt             # Dependencies
├── .gitignore                   # Schützt .env & Secrets
├── README.md                    # Diese Datei
└── DEPLOYMENT_GUIDE.md          # Detaillierte Deployment-Anleitung
```

---

## 🔧 Technologie-Stack

| Komponente | Beschreibung |
|-----------|------------|
| **Frontend** | [Streamlit](https://streamlit.io/) - einfache Web UI |
| **Backend** | Python + OpenAI SDK |
| **KI-Modell** | [Llama 3.1 70B](https://build.nvidia.com/meta/llama-3-1-70b-instruct) via NVIDIA NIM |
| **Hosting** | [Streamlit Cloud](https://streamlit.io/cloud) (kostenlos) |
| **Version Control** | Git + GitHub |

---

## 🎯 Wie der Agent funktioniert

```
┌─────────────────────────────────────────────┐
│ 1. INPUT: Benutzer gibt Problem ein        │
└─────────────────────┬───────────────────────┘
                      ▼
        ┌─────────────────────────┐
        │ 📋 PLANNING PHASE       │
        │ • Analysiert Problem    │
        │ • Erstellt Lösungsplan  │
        │ • Definiert Kriterien   │
        └──────────┬──────────────┘
                   ▼
        ┌─────────────────────────┐
        │ 🚀 EXECUTION PHASE      │
        │ • Setzt Plan um         │
        │ • Entwickelt Lösung     │
        │ • Erstellt Summary      │
        └──────────┬──────────────┘
                   ▼
        ┌─────────────────────────┐
        │ ✅ VERIFICATION PHASE   │
        │ • Überprüft Lösung      │
        │ • Bewertet (0-10)       │
        │ • akzeptabel? ───┐      │
        └──────────────────┼──────┘
                           │
                ┌─ NEIN ───┼─ JA ───┐
                ▼                  ▼
        ┌─────────────────┐  2. OUTPUT: Finale Lösung
        │ 🔄 REFINEMENT   │  • Exportierbar
        │ • Verbessert    │  • Formatiert
        │ • Optimiert     │  • Evaluated
        │ • Loop: max 10x │
        └─────────────────┘
```

---

## 🔒 Sicherheit

✅ **API-Keys niemals im Code**
- Secrets auf Streamlit Cloud
- `.env` in `.gitignore`
- Environment Variables für lokale Entwicklung

✅ **Passwort-Schutz**
- Einfache Authentifizierung
- Ausloggen beim Schließen - später: Multi-User Support

✅ **Daten-Privacy**
- Keine Speicherung von Eingaben
- Stateless Design
- Direkte API-Anfragen

---

## 🚦 Roadmap

- [ ] **Multi-User Support** mit User-Accounts
- [ ] **Chat History** - Vergangene Anfragen speichern
- [ ] **Custom Models** - Andere LLMs auswählen
- [ ] **API Integration** - REST API für externe Apps
- [ ] **Analytics Dashboard** - Nutzungsstatistiken
- [ ] **Voice Input** - Spracherkennung
- [ ] **Dark Mode** - Theme Switcher

---

## 🤝 Beitragen

Contributions sind willkommen! So kannst du helfen:

1. Fork das Repository
2. Feature Branch erstellen (`git checkout -b feature/neue-features`)
3. Änderungen commiten (`git commit -m 'Add neue Features'`)
4. Branch pushen (`git push origin feature/neue-features`)
5. Pull Request öffnen

---

## ⚖️ Lizenz

Dieses Projekt ist unter der **MIT Lizenz** lizensiert - siehe [LICENSE](LICENSE) für Details.

---

## 📞 Support & Kontakt

Hast du Fragen oder Probleme?

- 📧 **Issues**: [GitHub Issues](https://github.com/yourusername/ai-agent/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/ai-agent/discussions)
- 📚 **Dokumentation**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 🙏 Danksagungen

- 🔧 [Streamlit](https://streamlit.io/) - Für das großartige Framework
- 🚀 [NVIDIA NIM](https://build.nvidia.com/) - Kostenlos Zugang zu LLMs
- 🤖 [Meta Llama](https://www.meta.com/research/llama/) - Für das großartige Modell

---

## 📊 Status

![GitHub Stars](https://img.shields.io/github/stars/yourusername/ai-agent?style=social)
![GitHub Forks](https://img.shields.io/github/forks/yourusername/ai-agent?style=social)
![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

---

**Made with ❤️ by [Your Name]**

*Last updated: 2026-04-13*
