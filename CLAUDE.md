# CLAUDE.md

Dieses Workspace ist **Jarvis** — ein persoenlicher KI-Assistent mit Sprachsteuerung.

---

## Fuer Claude Code: Setup-Modus

Wenn der Nutzer nach dem Setup fragt oder "Richte Jarvis ein" sagt, folge den Anweisungen in `SETUP.md`. Frage den Nutzer nach seinem Namen, seiner Taetigkeit, und wie er angesprochen werden moechte — diese Infos muessen in den Systemprompt in `server.py` eingetragen werden (ersetze die aktuellen Platzhalter "Julian", "KI-Berater und Automatisierungsexperte", "Sir").

**WICHTIG — Pruefe und installiere zuerst alle Voraussetzungen:**

1. **Python**: Pruefe ob Python 3.10+ installiert ist (`python --version`). Falls nicht, installiere es:
   - Windows: `winget install Python.Python.3.12`
   - Warte bis die Installation abgeschlossen ist und pruefe erneut

2. **Google Chrome**: Pruefe ob Chrome installiert ist. Falls nicht, weise den Nutzer an Chrome von https://google.com/chrome zu installieren.

3. **pip Dependencies**: `pip install -r requirements.txt`

4. **Playwright Browser**: `playwright install chromium`

Erst NACHDEM alle Voraussetzungen installiert sind, fahre mit dem Setup in `SETUP.md` fort (API Keys abfragen, config.json erstellen, etc.).

---

## Workspace Structure

```
.
├── CLAUDE.md              # This file
├── SETUP.md               # Setup-Anleitung fuer Claude Code
├── config.json            # Persoenliche Config (gitignored)
├── config.example.json    # Template mit Platzhaltern
├── requirements.txt       # Python Dependencies
├── server.py              # FastAPI Backend (LLM via OpenAI-kompatibles Endpoint + TTS)
├── browser_tools.py       # Playwright Browser-Steuerung
├── screen_capture.py      # Screenshot + Vision-LLM
├── frontend/
│   ├── index.html         # Jarvis Web-UI
│   ├── main.js            # Speech Recognition + WebSocket + Audio
│   └── style.css          # Dark Theme mit Orb-Animation
└── tts.py                 # TTS-Backends (Piper lokal / ElevenLabs)
```

---

## Interessante LLMs fuer den Agent

Kandidaten fuer `llm_chat_model` in `config.json`. Kriterien: **geringe Latenz, ausreichend intelligent, guenstig**. Alle aktuell ueber OpenRouter verfuegbar.

| Modell | Hinweis |
|---|---|
| `qwen/qwen3.5-flash-02-23` | Aktuell im Einsatz |
| Qwen3.6 Flash (35B-A3M) | Nachfolger von 3.5 — noch nicht auf OpenRouter, wird aber erwartet |
| `xiaomi/mimo-v2-flash` | Solide, war unser Default |
| `stepfun/step-3.5-flash` | Ebenfalls stark im Flash-Segment — https://openrouter.ai/stepfun/step-3.5-flash |

Stand der Liste: 2026-04. Neue Flash-Versionen bei https://openrouter.ai/models pruefen.

---

## Refactor-Richtung (wo wir weitermachen)

**Projektziel:** Dieses Fork-Repo soll ein schlanker, Linux-tauglicher Voice-Agent werden — natuerliche Unterhaltung als Kern, spaeter Recherche-Delegation und ein Gedaechtnis auf Obsidian-Basis. Das urspruengliche Template (Julian) hatte viele Windows-Automatisierungs-Features, die fuer diesen Zweck nicht gebraucht werden und schrittweise rausgeworfen werden.

**Bereits gemacht:**
- LLM-Config generisch ueber OpenAI-kompatibles Endpoint (OpenRouter Default)
- Launch-Session-Scripts + Clap-Trigger komplett entfernt, zugehoerige Config-Keys (`workspace_path`, `spotify_track`, `browser_url`, `apps`) aus Example + persoenlicher Config raus
- TTS-Abstraktion (Piper lokal / ElevenLabs) und Whisper-STT im Frontend bereits drin

**Als naechstes aufraeumen:**
1. **Browser-Automation** (`browser_tools.py`, `[ACTION:SEARCH|OPEN|BROWSE|NEWS]` in `server.py`) — passt nicht zum "natuerliches Gespraech"-Kern und blaeht den Systemprompt auf. Raus bis die Recherche-Delegation als richtiger Agent nachgezogen wird.
2. **Screen-Vision** (`screen_capture.py`, `[ACTION:SCREEN]`, `llm_vision_model` in Config) — `PIL.ImageGrab` funktioniert unter Wayland nicht zuverlaessig, und der Use-Case ist nebensaechlich. Raus.
3. **Windows-Doku** in `SETUP.md` + `CLAUDE.md` aktualisieren (Voraussetzungen, `winget install`, Task Scheduler, `taskkill` im Troubleshooting, `C:\`-Pfade) — Linux/Mac-Pfade und -Befehle statt Windows-only.
4. **README.md** hat noch viel veraltetes Marketing-Material (Claude-Haiku-Architekturdiagramm, Double-Clap-Erwaehnungen die ich evtl. uebersehen habe, "Built for Windows"-Mac-Sektion, Anthropic-API-Tabelle). Grundsaetzlich ueberarbeiten oder eindampfen.
5. **Systemprompt in `server.py`** entschlacken sobald Browser + Screen weg sind — die Action-Tag-Dokumentation macht dann gut die Haelfte des Prompts aus und ist ueberfluessig.

**Spaetere Features (nicht jetzt):**
- Recherche-Delegation als Sub-Agent (Jarvis ruft einen Agent mit Web-Such-Tools auf, bekommt Zusammenfassung zurueck)
- Gedaechtnis via Obsidian (Jarvis kann Fakten persistent in Obsidian-Notes ablegen und beim naechsten Start laden)
