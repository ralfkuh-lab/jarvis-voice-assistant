"""
Jarvis V2 — Screen Capture
Takes screenshots and describes them via a Vision model over any
OpenAI-compatible endpoint.
"""

import base64
import io
from PIL import ImageGrab


def capture_screen() -> bytes:
    """Capture the entire screen, return PNG bytes."""
    img = ImageGrab.grab()
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def describe_screen(llm_client, model: str) -> str:
    """Capture screen and describe it using the configured vision-capable model."""
    png_bytes = capture_screen()
    b64 = base64.b64encode(png_bytes).decode("utf-8")

    response = llm_client.chat.completions.create(
        model=model,
        max_tokens=300,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                },
                {
                    "type": "text",
                    "text": "Beschreibe kurz auf Deutsch was auf diesem Bildschirm zu sehen ist. Maximal 2-3 Saetze. Nenne die wichtigsten offenen Programme und Inhalte.",
                },
            ],
        }],
    )
    return response.choices[0].message.content
