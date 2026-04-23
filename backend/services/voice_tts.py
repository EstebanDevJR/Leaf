"""Text-to-Speech service using Piper TTS (offline, Spanish)."""

import io
import logging
import os
import wave

logger = logging.getLogger(__name__)


class VoiceTTS:
    """Synthesizes text to WAV audio using Piper TTS (offline)."""

    def __init__(self):
        self._voice = None

    def _load_voice(self):
        if self._voice is None:
            try:
                from piper.voice import PiperVoice
            except ImportError:
                raise RuntimeError(
                    "piper-tts no instalado — ejecuta: uv add piper-tts"
                )
            model_path = os.getenv(
                "PIPER_VOICE_PATH", "models/es_ES-davefx-medium.onnx"
            )
            if not os.path.exists(model_path):
                raise RuntimeError(
                    f"Modelo Piper no encontrado en {model_path}. "
                    "Descárgalo desde https://github.com/rhasspy/piper/releases"
                )
            self._voice = PiperVoice.load(model_path)
        return self._voice

    def synthesize(self, text: str) -> bytes:
        """Return WAV bytes for the given text. Returns empty bytes on failure."""
        try:
            voice = self._load_voice()
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_file:
                voice.synthesize(text, wav_file)
            return buf.getvalue()
        except Exception as e:
            logger.error("VoiceTTS.synthesize error: %s", e)
            return b""
