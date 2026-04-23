"""STT using Groq's Whisper API — free tier, ~0.3s latency, Spanish-optimized.

Free tier: 7,200 audio requests/day (whisper-large-v3).
Sign up at https://console.groq.com — no credit card required.
"""

import logging
import os

logger = logging.getLogger(__name__)


class GroqSTT:
    """Transcribes audio via Groq's hosted Whisper large-v3."""

    MODEL = "whisper-large-v3"

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
            except ImportError:
                raise RuntimeError("groq no instalado — ejecuta: uv add groq")
            from backend.config import settings
            api_key = settings.groq_api_key or os.getenv("GROQ_API_KEY", "")
            if not api_key:
                raise RuntimeError("GROQ_API_KEY no configurada en .env")
            self._client = Groq(api_key=api_key)
        return self._client

    def transcribe(self, audio_path: str) -> str:
        """Send audio file to Groq and return the Spanish transcript."""
        try:
            client = self._get_client()
            with open(audio_path, "rb") as f:
                result = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), f.read()),
                    model=self.MODEL,
                    language="es",
                    response_format="text",
                )
            transcript = str(result).strip()
            logger.info("Groq STT transcript: %s", transcript)
            return transcript
        except Exception as e:
            logger.error("GroqSTT.transcribe error: %s", e)
            return ""
