"""
Jarvis V2 — Voice AI Server
FastAPI backend: receives speech text, thinks with an LLM over any
OpenAI-compatible endpoint (OpenRouter, OpenAI, Ollama, ...),
speaks with ElevenLabs, controls browser with Playwright.
"""

import asyncio
import base64
import json
import os
import re
import time

import httpx
from openai import OpenAI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import tts as tts_module

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

LLM_API_KEY = config["llm_api_key"]
LLM_BASE_URL = config.get("llm_base_url", "https://openrouter.ai/api/v1")
LLM_CHAT_MODEL = config.get("llm_chat_model", "xiaomi/mimo-v2-flash")
LLM_VISION_MODEL = config.get("llm_vision_model", "google/gemini-2.5-flash")
ELEVENLABS_API_KEY = config["elevenlabs_api_key"]
ELEVENLABS_VOICE_ID = config.get("elevenlabs_voice_id", "rDmv3mOhK6TnhYWckFaD")
USER_NAME = config.get("user_name", "Ralf")
USER_ADDRESS = config.get("user_address", "Chef")
CITY = config.get("city", "Ahaus")
TASKS_FILE = config.get("obsidian_inbox_path", "")

llm_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
http = httpx.AsyncClient(timeout=30)

tts_backend = tts_module.build_backend(config, http)
print(f"[jarvis] TTS-Backend: {type(tts_backend).__name__}", flush=True)

WHISPER_URL = config.get("whisper_url", "http://127.0.0.1:8350/transcribe")
WHISPER_PROMPT = "Jarvis, Ralf, Ahaus, Obsidian, GitHub, Playwright, Claude, OpenRouter, ElevenLabs, Whisper, Spotify"

app = FastAPI()

import browser_tools
import screen_capture


def get_weather_sync():
    """Fetch raw weather data at startup."""
    import urllib.request
    try:
        req = urllib.request.Request(f"https://wttr.in/{CITY}?format=j1", headers={"User-Agent": "curl"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        c = data["current_condition"][0]
        return {
            "temp": c["temp_C"],
            "feels_like": c["FeelsLikeC"],
            "description": c["weatherDesc"][0]["value"],
            "humidity": c["humidity"],
            "wind_kmh": c["windspeedKmph"],
        }
    except:
        return None


def get_tasks_sync():
    """Read open tasks from Obsidian (sync)."""
    if not TASKS_FILE:
        return []
    try:
        tasks_path = os.path.join(TASKS_FILE, "Tasks.md")
        with open(tasks_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.strip().replace("- [ ]", "").strip() for l in lines if l.strip().startswith("- [ ]")]
    except:
        return []


def refresh_data():
    """Refresh weather and tasks."""
    global WEATHER_INFO, TASKS_INFO
    WEATHER_INFO = get_weather_sync()
    TASKS_INFO = get_tasks_sync()
    print(f"[jarvis] Wetter: {WEATHER_INFO}", flush=True)
    print(f"[jarvis] Tasks: {len(TASKS_INFO)} geladen", flush=True)

WEATHER_INFO = ""
TASKS_INFO = []
refresh_data()

# Action parsing
ACTION_PATTERN = re.compile(r'\[ACTION:(\w+)\]\s*(.*?)$', re.DOTALL | re.MULTILINE)

conversations: dict[str, list] = {}

def build_system_prompt():
    weather_block = ""
    if WEATHER_INFO:
        w = WEATHER_INFO
        weather_block = f"\nWetter {CITY}: {w['temp']}°C, gefuehlt {w['feels_like']}°C, {w['description']}"

    task_block = ""
    if TASKS_INFO:
        task_block = f"\nOffene Aufgaben ({len(TASKS_INFO)}): " + ", ".join(TASKS_INFO[:5])

    return f"""Du bist Jarvis, der KI-Assistent von Tony Stark aus Iron Man. Dein Dienstherr ist {USER_NAME}, ein Software-Entwickler. Du sprichst ausschliesslich Deutsch. {USER_NAME} moechte mit "{USER_ADDRESS}" angeredet und gesiezt werden. Nutze "Sie" als Pronomen — FALSCH: "{USER_ADDRESS} planen", RICHTIG: "Sie planen, {USER_ADDRESS}". Dein Ton ist trocken, sarkastisch und britisch-hoeflich - wie ein Butler der alles gesehen hat und trotzdem loyal bleibt. Du machst subtile, trockene Bemerkungen, bist aber niemals respektlos. Wenn {USER_ADDRESS} eine offensichtliche Frage stellt, darfst du mit elegantem Sarkasmus antworten. Du bist hochintelligent, effizient und immer einen Schritt voraus. Halte deine Antworten kurz - maximal 3 Saetze. Du kommentierst fragwuerdige Entscheidungen hoeflich aber spitz.

WICHTIG: Schreibe NIEMALS Regieanweisungen, Emotionen oder Tags in eckigen Klammern wie [sarcastic] [formal] [amused] [dry] oder aehnliches. Dein Sarkasmus muss REIN durch die Wortwahl kommen. Alles was du schreibst wird laut vorgelesen.

Du hast die volle Kontrolle ueber den Browser von {USER_NAME}. Du kannst im Internet suchen, Webseiten oeffnen und den Bildschirm sehen. Wenn Sir dich bittet etwas nachzuschauen, zu recherchieren, zu googeln, eine Seite zu oeffnen, oder irgendetwas im Internet zu tun — nutze IMMER eine Aktion. Frag nicht ob du es tun sollst, tu es einfach.

AKTIONEN - Schreibe die passende Aktion ans ENDE deiner Antwort. Der Text VOR der Aktion wird vorgelesen, die Aktion selbst wird still ausgefuehrt.
[ACTION:SEARCH] suchbegriff - Internet durchsuchen und Ergebnisse zusammenfassen
[ACTION:OPEN] url - URL im Browser oeffnen
[ACTION:SCREEN] - Bildschirm ansehen und beschreiben. WICHTIG: Bei SCREEN schreibe NUR die Aktion, KEINEN Text davor. Also NUR "[ACTION:SCREEN]" und sonst nichts.
[ACTION:NEWS] - Aktuelle Weltnachrichten abrufen. Nutze diese Aktion wenn nach News, Nachrichten, was in der Welt passiert, aktuelle Lage oder Weltgeschehen gefragt wird. Schreibe einen kurzen Satz davor wie "Ich schaue nach den aktuellen Nachrichten."

WENN {USER_NAME} "Jarvis activate" sagt:
- Begruesse ihn passend zur Tageszeit (aktuelle Zeit: {{time}}).
- Gebe eine kurze Info ueber das Wetter — Temperatur und ob Sonne/klar/bewoelkt/Regen, und wie es sich anfuehlt. Keine Luftfeuchtigkeit.
- Fasse die Aufgaben kurz als Ueberblick in einem Satz zusammen, ohne dabei jede einzelne Aufgabe einfach vorzulesen. Gebe gerne einen humorvollen Kommentar am Ende an.
- Sei kreativ bei der Begruessung.

=== AKTUELLE DATEN ==={weather_block}{task_block}
==="""


def get_system_prompt():
    return build_system_prompt().replace("{time}", time.strftime("%H:%M"))


def extract_action(text: str):
    match = ACTION_PATTERN.search(text)
    if match:
        clean = text[:match.start()].strip()
        return clean, {"type": match.group(1), "payload": match.group(2).strip()}
    return text, None


def split_for_streaming(text: str, max_len: int = 200) -> list[str]:
    """Splitte Text in satzweise Chunks für progressives TTS-Streaming.

    Kurze Sätze werden gemerged, bis max_len erreicht ist. Das vermeidet hörbare
    Pausen zwischen zu vielen winzigen Chunks.
    """
    text = text.strip()
    if not text:
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if not s:
            continue
        if len(current) + len(s) > max_len and current:
            chunks.append(current.strip())
            current = s
        else:
            current = (current + " " + s).strip()
    if current:
        chunks.append(current.strip())
    return chunks


async def stream_tts(text: str, ws: WebSocket, first_text: str | None = None):
    """Synthetisiere Text satzweise und sende jeden Chunk sofort per WebSocket.

    Alle Chunks werden parallel generiert, aber in korrekter Reihenfolge gesendet,
    damit das Frontend sie in der Queue nacheinander abspielt.
    """
    chunks = split_for_streaming(text)
    if not chunks:
        return

    tasks = [asyncio.create_task(tts_backend.synthesize(c)) for c in chunks]
    for i, task in enumerate(tasks):
        audio, mime = await task
        print(f"  TTS[{i+1}/{len(chunks)}]: {len(audio)} bytes ({mime})", flush=True)
        await ws.send_json({
            "type": "response",
            "text": first_text if i == 0 else "",
            "audio": base64.b64encode(audio).decode("utf-8") if audio else "",
            "mime": mime,
        })


async def execute_action(action: dict) -> str:
    t = action["type"]
    p = action["payload"]

    if t == "SEARCH":
        result = await browser_tools.search_and_read(p)
        if "error" not in result:
            return f"Seite: {result.get('title', '')}\nURL: {result.get('url', '')}\n\n{result.get('content', '')[:2000]}"
        return f"Suche fehlgeschlagen: {result.get('error', '')}"

    elif t == "BROWSE":
        result = await browser_tools.visit(p)
        if "error" not in result:
            return f"Seite: {result.get('title', '')}\n\n{result.get('content', '')[:2000]}"
        return f"Seite nicht erreichbar: {result.get('error', '')}"

    elif t == "OPEN":
        await browser_tools.open_url(p)
        return f"Geoeffnet: {p}"

    elif t == "SCREEN":
        return await screen_capture.describe_screen(llm_client, LLM_VISION_MODEL)

    elif t == "NEWS":
        result = await browser_tools.fetch_news()
        return result

    return ""


async def process_message(session_id: str, user_text: str, ws: WebSocket):
    """Process message and send responses via WebSocket."""
    if session_id not in conversations:
        conversations[session_id] = []

    # Refresh weather + tasks on activate
    if "activate" in user_text.lower():
        refresh_data()

    conversations[session_id].append({"role": "user", "content": user_text})
    history = conversations[session_id][-16:]

    # LLM call via configured OpenAI-compatible endpoint
    response = llm_client.chat.completions.create(
        model=LLM_CHAT_MODEL,
        max_tokens=400,
        messages=[{"role": "system", "content": get_system_prompt()}] + history,
    )
    reply = response.choices[0].message.content
    print(f"  LLM raw: {reply[:200]}", flush=True)
    spoken_text, action = extract_action(reply)

    # Speak the main response immediately — streamed chunk-by-chunk
    if spoken_text:
        print(f"  Jarvis: {spoken_text[:80]}", flush=True)
        conversations[session_id].append({"role": "assistant", "content": spoken_text})
        await stream_tts(spoken_text, ws, first_text=spoken_text)

    # Execute action if any
    if action:
        print(f"  Action: {action['type']} -> {action['payload'][:100]}", flush=True)

        # Quick voice feedback for SCREEN so user knows Jarvis is working
        if action["type"] == "SCREEN":
            hint = "Lassen Sie mich einen Blick auf Ihren Bildschirm werfen."
            await stream_tts(hint, ws, first_text=hint)

        try:
            action_result = await execute_action(action)
            print(f"  Result: {action_result}", flush=True)
        except Exception as e:
            print(f"  Action error: {e}", flush=True)
            action_result = f"Fehler: {e}"

        if action["type"] == "OPEN":
            # Just opened browser, nothing to summarize
            return

        # SEARCH, BROWSE, SCREEN — summarize results
        if action_result and "fehlgeschlagen" not in action_result:
            summary_resp = llm_client.chat.completions.create(
                model=LLM_CHAT_MODEL,
                max_tokens=250,
                messages=[{"role": "system", "content": f"Du bist Jarvis. Fasse die folgenden Informationen KURZ auf Deutsch zusammen, maximal 3 Saetze, im Jarvis-Stil. Sprich den Nutzer als {USER_ADDRESS} an. KEINE Tags in eckigen Klammern. KEINE ACTION-Tags."}, {"role": "user", "content": f"Fasse zusammen:\n\n{action_result}"}],
            )
            summary = summary_resp.choices[0].message.content
            summary, _ = extract_action(summary)
        else:
            summary = f"Das hat leider nicht funktioniert, {USER_ADDRESS}."

        conversations[session_id].append({"role": "assistant", "content": summary})
        await stream_tts(summary, ws, first_text=summary)


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Sende rohe Float32 PCM @ 16kHz an den lokalen Whisper-Server."""
    try:
        resp = await http.post(
            WHISPER_URL,
            params={"prompt": WHISPER_PROMPT},
            content=audio_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json().get("text", "").strip()
        print(f"  Whisper error: {resp.status_code} {resp.text[:200]}", flush=True)
    except Exception as e:
        print(f"  Whisper exception: {e}", flush=True)
    return ""


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(id(ws))
    print(f"[jarvis] Client connected", flush=True)

    try:
        while True:
            msg = await ws.receive()
            if msg.get("type") == "websocket.disconnect":
                break

            if "bytes" in msg and msg["bytes"]:
                await ws.send_json({"type": "status", "text": "Transkribiere..."})
                user_text = await transcribe_audio(msg["bytes"])
                if not user_text:
                    await ws.send_json({"type": "status", "text": ""})
                    continue
                await ws.send_json({"type": "transcription", "text": user_text})
                print(f"  You:    {user_text}", flush=True)
                await process_message(session_id, user_text, ws)
            elif "text" in msg and msg["text"]:
                try:
                    data = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue
                print(f"  You:    {user_text}", flush=True)
                await process_message(session_id, user_text, ws)

    except WebSocketDisconnect:
        conversations.pop(session_id, None)


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "frontend")), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "frontend", "index.html"))


if __name__ == "__main__":
    import uvicorn
    print("=" * 50, flush=True)
    print("  J.A.R.V.I.S. V2 Server", flush=True)
    print(f"  http://localhost:8340", flush=True)
    print("=" * 50, flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8340)
