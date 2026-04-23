"""Speech-to-Text service using faster-whisper (offline, cross-platform)."""

import logging
import os

logger = logging.getLogger(__name__)

# Model size: "tiny", "base", "small", "medium". "small" is the best speed/accuracy tradeoff.
_WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")


class VoiceSTT:
    """Transcribes audio to text using faster-whisper (runs fully offline after first download)."""

    def __init__(self):
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError:
                raise RuntimeError(
                    "faster-whisper no instalado — ejecuta: uv sync"
                )
            # Downloads model to ~/.cache/huggingface on first run
            self._model = WhisperModel(
                _WHISPER_MODEL_SIZE,
                device="cpu",
                compute_type="int8",  # int8 is fastest on CPU
            )
            logger.info("Whisper model '%s' cargado.", _WHISPER_MODEL_SIZE)
        return self._model

    def transcribe(self, audio_path: str) -> str:
        """Transcribe any audio file to text. Returns empty string on failure."""
        try:
            model = self._load_model()
            segments, info = model.transcribe(
                audio_path,
                language="es",
                beam_size=5,
                vad_filter=True,        # skip silent parts automatically
                vad_parameters={"min_silence_duration_ms": 500},
            )
            logger.info("Detected language: %s (%.0f%%)", info.language, info.language_probability * 100)
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as e:
            logger.error("VoiceSTT.transcribe error: %s", e)
            return ""
