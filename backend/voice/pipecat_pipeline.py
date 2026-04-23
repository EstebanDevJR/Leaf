"""Voice pipeline — STT → LangGraph Orchestrator → TTS.

STT priority:
  1. Phi-4-multimodal (HuggingFace) — audio-native, mejor comprensión contextual
  2. faster-whisper (fallback) — si phi4 no carga (VRAM insuficiente, etc.)
"""

import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


def _make_stt():
    """Returns the best available STT backend."""
    try:
        from backend.services.phi4_voice import get_phi4_stt
        stt = get_phi4_stt()
        # Trigger model load now so errors surface early
        stt._load()
        logger.info("STT: usando Phi-4-multimodal")
        return stt
    except Exception as e:
        logger.warning("Phi-4-multimodal no disponible (%s) — usando faster-whisper.", e)
        from backend.services.voice_stt import VoiceSTT
        return VoiceSTT()


class VoicePipeline:
    """STT → LLM → TTS pipeline for a single voice session."""

    def __init__(self):
        self._stt = None
        self._tts = None

    def _get_stt(self):
        if self._stt is None:
            self._stt = _make_stt()
        return self._stt

    def _get_tts(self):
        if self._tts is None:
            from backend.services.voice_tts import VoiceTTS
            self._tts = VoiceTTS()
        return self._tts

    async def transcribe(self, wav_bytes: bytes) -> str:
        """Stage 1: WAV bytes → transcript string."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name
        try:
            return await asyncio.to_thread(self._get_stt().transcribe, tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def think(self, transcript: str) -> str:
        """Stage 2: transcript → agent response text (LangGraph + tools)."""
        from backend.agents.orchestrator import get_voice_agent
        agent = get_voice_agent()
        result = await asyncio.to_thread(
            agent.invoke,
            {"messages": [{"role": "user", "content": transcript}]},
        )
        messages = result.get("messages", [])
        return next(
            (
                m.content
                for m in reversed(messages)
                if hasattr(m, "content") and m.content and m.type == "ai"
            ),
            "No pude procesar tu mensaje.",
        )

    async def synthesize(self, text: str) -> bytes:
        """Stage 3: agent text → WAV bytes."""
        return await asyncio.to_thread(self._get_tts().synthesize, text)

    async def process(self, wav_bytes: bytes) -> tuple[str, str, bytes]:
        """Run the full pipeline. Returns (transcript, response_text, audio_wav)."""
        transcript = await self.transcribe(wav_bytes)
        if not transcript:
            fallback_text = "No te entendí bien, ¿puedes repetir?"
            audio = await self.synthesize(fallback_text)
            return ("", fallback_text, audio)

        response_text = await self.think(transcript)
        audio = await self.synthesize(response_text[:600])
        return (transcript, response_text, audio)
