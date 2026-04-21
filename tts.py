"""Text-to-Speech-Abstraktion für Jarvis.

Backend wird per config["tts_backend"] gesteuert:
- "piper"      — lokale Piper-TTS (kein Internet, schnell)
- "elevenlabs" — ElevenLabs Cloud

Jede synthesize()-Funktion liefert (audio_bytes, mime_type).
"""

import asyncio
import io
import os
import wave
from typing import Tuple


class PiperBackend:
    mime = "audio/wav"

    def __init__(self, model_path: str):
        from piper import PiperVoice
        self._voice = PiperVoice.load(model_path)

    def _synth_sync(self, text: str) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            self._voice.synthesize_wav(text, wf)
        return buf.getvalue()

    async def synthesize(self, text: str) -> Tuple[bytes, str]:
        if not text.strip():
            return b"", self.mime
        loop = asyncio.get_running_loop()
        audio = await loop.run_in_executor(None, self._synth_sync, text)
        return audio, self.mime


class ElevenLabsBackend:
    mime = "audio/mpeg"

    def __init__(self, api_key: str, voice_id: str, http_client):
        self._api_key = api_key
        self._voice_id = voice_id
        self._http = http_client

    async def synthesize(self, text: str) -> Tuple[bytes, str]:
        if not text.strip():
            return b"", self.mime
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self._voice_id}"
        try:
            resp = await self._http.post(
                url,
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.85},
                },
            )
            if resp.status_code == 200:
                return resp.content, self.mime
            print(f"  ElevenLabs error {resp.status_code}: {resp.text[:200]}", flush=True)
        except Exception as e:
            print(f"  ElevenLabs exception: {e}", flush=True)
        return b"", self.mime


def build_backend(config: dict, http_client):
    name = config.get("tts_backend", "piper").lower()
    if name == "piper":
        model = config.get("piper_model_path") or os.path.join(
            os.path.dirname(__file__), "models", "de_DE-thorsten-high.onnx"
        )
        return PiperBackend(model)
    if name == "elevenlabs":
        return ElevenLabsBackend(
            config["elevenlabs_api_key"],
            config.get("elevenlabs_voice_id", ""),
            http_client,
        )
    raise ValueError(f"Unbekanntes tts_backend: {name}")
