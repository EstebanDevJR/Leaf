import base64

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import settings
from backend.tools.extract_receipt import extract_receipt_from_image, debug_extract

router = APIRouter()

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


@router.post("/extract")
async def extract_receipt_endpoint(file: UploadFile = File(...)) -> dict:
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de archivo no soportado: {file.content_type}. Usa JPEG, PNG o WebP.",
        )

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Imagen demasiado grande (máx. 10 MB).")

    image_b64 = base64.b64encode(contents).decode()

    try:
        data = await extract_receipt_from_image(image_b64)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Error al comunicarse con Ollama ({settings.ollama_model}): {exc}",
        ) from exc

    return data


@router.post("/debug")
async def debug_receipt_endpoint(file: UploadFile = File(...)) -> dict:
    """Muestra los pasos intermedios: texto Moondream y JSON crudo de gemma4."""
    contents = await file.read()
    image_b64 = base64.b64encode(contents).decode()
    try:
        return await debug_extract(image_b64)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
