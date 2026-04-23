"""Voice pipeline — Groq STT → Groq LLM → gTTS (sentence streaming)."""

import asyncio
import logging
import os
import re
import tempfile
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences suitable for TTS chunking."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) > 100:
            sub = re.split(r'(?<=,)\s+', part)
            result.extend(s.strip() for s in sub if s.strip())
        else:
            result.append(part)
    return result


class VoicePipeline:
    """Groq STT → Groq LLM agent → gTTS, streamed sentence by sentence."""

    def __init__(self):
        self._stt = None
        self._tts = None

    def _get_stt(self):
        if self._stt is None:
            from backend.services.stt_factory import get_stt
            self._stt = get_stt()
        return self._stt

    def _get_tts(self):
        if self._tts is None:
            from backend.services.voice_tts import VoiceTTS
            self._tts = VoiceTTS()
        return self._tts

    async def transcribe(self, audio_bytes: bytes, suffix: str = ".wav") -> str:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        try:
            return await asyncio.to_thread(self._get_stt().transcribe, tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def _think(self, transcript: str) -> str:
        try:
            from backend.config import settings
            from backend.agents.orchestrator import get_groq_voice_agent, get_agent
            agent = get_groq_voice_agent() if settings.groq_api_key else get_agent()
            result = await asyncio.to_thread(
                agent.invoke,
                {"messages": [{"role": "user", "content": transcript}]},
            )
            messages = result.get("messages", [])
            return next(
                (m.content for m in reversed(messages) if hasattr(m, "content") and m.content and m.type == "ai"),
                "No pude procesar tu mensaje.",
            )
        except Exception as e:
            logger.error("Voice think() failed: %s", e)
            return "No pude conectarme al agente. Verifica la configuración y vuelve a intentarlo."

    async def stream_process(self, audio_bytes: bytes, suffix: str = ".wav") -> AsyncIterator[dict]:
        """Async generator: yields transcript → response → audio_chunk(s) → done."""
        transcript = await self.transcribe(audio_bytes, suffix)
        yield {"type": "transcript", "text": transcript}

        if not transcript:
            fallback = "No te entendí bien, ¿puedes repetir?"
            audio = await asyncio.to_thread(self._get_tts().synthesize, fallback)
            if audio:
                yield {"type": "audio_chunk", "data": audio}
            yield {"type": "done"}
            return

        response_text = await self._think(transcript)
        yield {"type": "response", "text": response_text}

        sentences = _split_sentences(response_text) or [response_text]
        for sentence in sentences:
            if sentence.strip():
                audio = await asyncio.to_thread(self._get_tts().synthesize, sentence)
                if audio:
                    yield {"type": "audio_chunk", "data": audio}

        yield {"type": "done"}

    async def process(self, audio_bytes: bytes, suffix: str = ".wav") -> tuple[str, str, bytes]:
        transcript = ""
        response_text = ""
        all_audio = b""
        async for event in self.stream_process(audio_bytes, suffix):
            if event["type"] == "transcript":
                transcript = event["text"]
            elif event["type"] == "response":
                response_text = event["text"]
            elif event["type"] == "audio_chunk":
                all_audio += event["data"]
        return transcript, response_text, all_audio
