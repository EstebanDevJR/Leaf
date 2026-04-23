"""Voice WebSocket endpoint — real-time voice call with Leaf agent.

Protocol (JSON frames over WebSocket):
  Client → Server: {"type": "audio", "data": "<base64 WAV>"}
  Server → Client: {"type": "transcript", "text": "..."}
  Server → Client: {"type": "response",  "text": "..."}
  Server → Client: {"type": "audio",     "data": "<base64 WAV>"}
  Server → Client: {"type": "error",     "message": "..."}
  Server → Client: {"type": "done"}

REST fallback:
  POST /voice/chat  — multipart with audio file, returns JSON + audio URL
"""

import base64
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.responses import Response

from backend.voice.pipecat_pipeline import VoicePipeline

router = APIRouter()
logger = logging.getLogger(__name__)

# One pipeline per WebSocket session — keeps conversation context isolated
_sessions: dict[str, VoicePipeline] = {}


@router.websocket("/ws")
async def voice_ws(websocket: WebSocket):
    """WebSocket endpoint for real-time voice conversation."""
    await websocket.accept()
    session_id = str(uuid.uuid4())
    pipeline = VoicePipeline()
    _sessions[session_id] = pipeline
    logger.info("Voice session started: %s", session_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") != "audio":
                continue

            raw_b64 = data.get("data", "")
            if not raw_b64:
                await websocket.send_json({"type": "error", "message": "No audio data received."})
                continue

            try:
                wav_bytes = base64.b64decode(raw_b64)
            except Exception:
                await websocket.send_json({"type": "error", "message": "Invalid base64 audio."})
                continue

            try:
                transcript, response_text, audio_wav = await pipeline.process(wav_bytes)

                await websocket.send_json({"type": "transcript", "text": transcript})
                await websocket.send_json({"type": "response",   "text": response_text})

                if audio_wav:
                    await websocket.send_json({
                        "type": "audio",
                        "data": base64.b64encode(audio_wav).decode(),
                    })

                await websocket.send_json({"type": "done"})

            except Exception as e:
                logger.error("Voice pipeline error (session %s): %s", session_id, e)
                await websocket.send_json({
                    "type": "error",
                    "message": "Error procesando tu voz. Intenta de nuevo.",
                })

    except WebSocketDisconnect:
        logger.info("Voice session ended: %s", session_id)
    finally:
        _sessions.pop(session_id, None)


@router.post("/chat")
async def voice_chat(audio: UploadFile = File(...)):
    """One-shot REST endpoint: send WAV, get back JSON + base64 WAV response."""
    if not audio.content_type or "audio" not in audio.content_type:
        raise HTTPException(status_code=400, detail="Se requiere un archivo de audio WAV.")

    wav_bytes = await audio.read()
    pipeline = VoicePipeline()

    try:
        transcript, response_text, audio_wav = await pipeline.process(wav_bytes)
    except Exception as e:
        logger.error("voice_chat error: %s", e)
        raise HTTPException(status_code=500, detail="Error procesando el audio.")

    return {
        "transcript": transcript,
        "response": response_text,
        "audio": base64.b64encode(audio_wav).decode() if audio_wav else None,
    }


@router.get("/health")
def voice_health():
    return {"status": "ok", "active_sessions": len(_sessions)}
