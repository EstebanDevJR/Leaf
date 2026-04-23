"""Auto-download Piper TTS model on first run.

faster-whisper (STT) downloads its own model to ~/.cache/huggingface automatically
on first use — no manual step needed here.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

MODELS_DIR = Path(os.getenv("MODELS_DIR", "models"))

# rhasspy/piper-voices: v1.0.0 paths rotos en HF; usar rama main y voces actuales (voices.json).
# es_ES-mls_10246-medium ya no existe; davefx-medium es español peninsular ~63 MB.
_PIPER_HF = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium"
)
PIPER_MODEL_NAME = "es_ES-davefx-medium.onnx"
PIPER_URLS = {
    "es_ES-davefx-medium.onnx": f"{_PIPER_HF}/es_ES-davefx-medium.onnx",
    "es_ES-davefx-medium.onnx.json": f"{_PIPER_HF}/es_ES-davefx-medium.onnx.json",
}


def _piper_ready() -> bool:
    path = Path(os.getenv("PIPER_VOICE_PATH", str(MODELS_DIR / PIPER_MODEL_NAME)))
    return path.exists() and path.stat().st_size > 1_000_000


def _download_bytes(url: str) -> bytes:
    import httpx
    logger.info("Descargando %s ...", url)
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        received = 0
        chunks = []
        for chunk in r.iter_bytes(chunk_size=1 << 20):
            chunks.append(chunk)
            received += len(chunk)
            if total:
                pct = received * 100 // total
                if pct % 10 == 0:
                    logger.info("  Piper: %d%%", pct)
        return b"".join(chunks)


def ensure_piper():
    if _piper_ready():
        return
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Modelo Piper TTS no encontrado — descargando (~65 MB desde HuggingFace)...")
    for filename, url in PIPER_URLS.items():
        dest = MODELS_DIR / filename
        if not dest.exists():
            dest.write_bytes(_download_bytes(url))
            logger.info("  Guardado: %s", dest)
    logger.info("Piper TTS listo.")


def ensure_models():
    """Download Piper TTS if missing. Safe to call on every startup."""
    # faster-whisper downloads itself on first transcription — nothing to do for STT
    try:
        ensure_piper()
    except Exception as e:
        logger.warning("No se pudo descargar Piper TTS: %s — respuestas de voz serán solo texto.", e)
