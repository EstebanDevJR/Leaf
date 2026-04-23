"""Text-to-Speech via gTTS (Google TTS — free, no API key, returns MP3)."""

import io
import logging

logger = logging.getLogger(__name__)


class VoiceTTS:
    """Synthesizes Spanish text to MP3 bytes using Google TTS."""

    def synthesize(self, text: str) -> bytes:
        """Return MP3 bytes for the given text. Returns empty bytes on failure."""
        try:
            from gtts import gTTS
        except ImportError:
            raise RuntimeError("gtts no instalado — ejecuta: uv sync")
        try:
            tts = gTTS(text=text, lang="es", slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()
        except Exception as e:
            logger.error("VoiceTTS.synthesize error: %s", e)
            return b""
