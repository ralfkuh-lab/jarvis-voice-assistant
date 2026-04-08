# Jarvis Setup Guide

Dein persoenlicher KI-Assistent — inspiriert von Iron Mans Jarvis.

**Was du bekommst:**
- Zweimal klatschen → dein komplettes Arbeits-Setup startet
- Jarvis begruesst dich mit Wetter und deinen Aufgaben
- Du sprichst frei mit Jarvis — er antwortet per Stimme
- Jarvis kann deinen Browser steuern (suchen, Seiten oeffnen)
- Jarvis kann deinen Bildschirm sehen und beschreiben

---

## Voraussetzungen

- **Windows 10/11**
- **Python 3.10+**
- **Google Chrome** (fuer Spracheingabe + Jarvis UI)
- **Claude Code** installiert

---

## Setup starten

Oeffne diesen Ordner in VS Code, starte Claude Code, und sag:

> Richte Jarvis fuer mich ein.

Claude Code fragt dich dann nach:

1. **Dein Name** und wie du angesprochen werden willst (z.B. "Sir")
2. **Anthropic API Key** — von https://console.anthropic.com (fuer Claude Haiku, das Gehirn)
3. **ElevenLabs API Key** — von https://elevenlabs.io (fuer die Stimme)
4. **Spotify-Song** — Link zum Song der beim Start spielen soll
5. **Programme** — welche Apps sollen beim Doppelklatschen starten?
6. **Website** — welche Seite soll im Browser aufgehen?
7. **Stadt fuers Wetter** — z.B. Hamburg
8. **Obsidian Vault** — optional, welcher Ordner soll Jarvis kennen?

---

## Was Claude Code fuer dich einrichtet

### 1. Python-Dependencies
```
pip install -r requirements.txt
playwright install chromium
```

### 2. config.json erstellen
Claude Code erstellt `config.json` aus `config.example.json` mit deinen echten Daten:
```json
{
  "anthropic_api_key": "sk-ant-...",
  "elevenlabs_api_key": "sk_...",
  "elevenlabs_voice_id": "VOICE_ID",
  "user_name": "Dein Name",
  "user_address": "Sir",
  "city": "Hamburg",
  "workspace_path": "C:\\pfad\\zum\\jarvis_template",
  "spotify_track": "spotify:track:DEIN_TRACK_ID",
  "browser_url": "https://deine-website.com",
  "obsidian_inbox_path": "C:\\pfad\\zum\\obsidian\\inbox",
  "apps": ["obsidian://open"]
}
```

### 3. ElevenLabs Stimme
Eine deutsche Stimme auswaehlen und die Voice ID in die Config eintragen. Empfehlung: **Felix Serenitas** (Starter Plan noetig) oder eine der Standard-Stimmen (Free Plan).

### 4. Systemprompt
Der Systemprompt wird in `server.py` automatisch aus der Config generiert. Er enthaelt:
- Jarvis-Persoenlichkeit (trocken, sarkastisch, britisch-hoeflich)
- Siezen mit gewaehlter Anrede
- Wetter- und Aufgaben-Integration
- Browser-Steuerung via Action-Tags
- Screen-Capture-Faehigkeit

---

## Architektur

```
Mikrofon (Chrome) → Web Speech API → WebSocket → FastAPI Server
                                                      ↓
                                                Claude Haiku (denkt)
                                                      ↓
                                    ┌─────────────────┼──────────────────┐
                                    ↓                 ↓                  ↓
                            ElevenLabs TTS     Playwright Browser   Screen Capture
                            (spricht)          (sucht/oeffnet)     (sieht Bildschirm)
                                    ↓
                            Audio → Browser Speaker
```

---

## Starten

### Jarvis manuell starten
```
python server.py
```
Dann http://localhost:8340 in Chrome oeffnen.

### Alles per Doppelklatschen starten
```
python scripts\clap-trigger.py
```
Zweimal klatschen → Spotify, VS Code, Obsidian, Chrome mit Jarvis starten automatisch.

### Clap Trigger beim Windows-Start
1. `Win + R` → `taskschd.msc`
2. Aufgabe erstellen → Trigger: "Bei Anmeldung"
3. Aktion: `powershell` mit Argument:
   `-ExecutionPolicy Bypass -WindowStyle Hidden -Command "python C:\DEIN\PFAD\scripts\clap-trigger.py"`

---

## Was Jarvis kann

- **"Wie ist das Wetter?"** → kennt das aktuelle Wetter
- **"Such nach MiroFish"** → oeffnet Browser, sucht, liest Ergebnisse
- **"Oeffne skool.com"** → oeffnet die Seite im Browser
- **"Was siehst du auf meinem Bildschirm?"** → macht Screenshot, beschreibt was er sieht
- **Jede Frage** → antwortet im Jarvis-Stil mit Stimme

---

## Fehlerbehebung

| Problem | Loesung |
|---|---|
| Jarvis spricht nicht | Pruefen ob Server laeuft (`python server.py`) und Chrome offen ist |
| "Verbindung verloren" | Alter Server-Prozess laeuft noch → `taskkill /f /im python.exe` und neu starten |
| Klatschen wird nicht erkannt | Threshold in `clap-trigger.py` anpassen |
| Browser-Suche geht nicht | `playwright install chromium` ausfuehren |
| Kein Audio im Browser | Einmal auf die Seite klicken (Chrome Autoplay-Policy) |

---

## Fuer Claude Code: Setup-Anweisungen

Wenn ein Nutzer "Richte Jarvis ein" sagt, fuehre folgende Schritte aus:

1. Frage nach: Name, Anrede, Anthropic API Key, ElevenLabs API Key, Spotify-Song (Link), Programme, Website, Stadt, Obsidian-Pfad (optional)

2. Installiere Dependencies:
   ```
   pip install -r requirements.txt
   playwright install chromium
   ```

3. Erstelle `config.json` aus `config.example.json` mit den Nutzerdaten

4. Finde eine passende ElevenLabs-Stimme:
   - Liste verfuegbare Stimmen via API
   - Empfehle eine deutsche Stimme
   - Trage die Voice ID in die Config ein

5. Passe `scripts/launch-session.ps1` an falls noetig (Pfade)

6. Teste: `python server.py` → http://localhost:8340 oeffnen

7. Richte optional den Autostart ein (Task Scheduler)

---

## Credits

Template von Julian — [Skool Community](https://skool.com/ki-automatisierung)
