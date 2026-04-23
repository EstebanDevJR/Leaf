"""STT backend factory — Groq Whisper API (cloud, free tier, ~0.3 s)."""

import logging

logger = logging.getLogger(__name__)


def get_stt():
    """Return the Groq STT instance. Raises on misconfiguration."""
    from backend.services.groq_stt import GroqSTT
    stt = GroqSTT()
    stt._get_client()  # fail fast if key is missing or groq not installed
    logger.info("STT: Groq Whisper activo.")
    return stt
