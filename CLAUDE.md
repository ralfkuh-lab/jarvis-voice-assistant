# CLAUDE.md

Dieses Workspace ist **Jarvis** — ein persoenlicher KI-Assistent mit Sprachsteuerung, Browser-Kontrolle und Doppelklatschen-Trigger.

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
└── scripts/
    ├── clap-trigger.py    # Doppelklatschen-Erkennung
    └── launch-session.ps1 # Startet alle Apps + Jarvis
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
