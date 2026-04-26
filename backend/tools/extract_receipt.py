import asyncio
import base64
import io
import json
import re

import ollama
from langchain_core.tools import tool
from PIL import Image, ImageEnhance

from backend.config import settings

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["es", "en"], gpu=False, verbose=False)
    return _reader


def _preprocess(image_b64: str):
    """Aumenta contraste y nitidez para mejorar la lectura de texto impreso."""
    import numpy as np
    raw = base64.b64decode(image_b64)
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    if min(w, h) < 1000:
        scale = 1000 / min(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.8)
    img = ImageEnhance.Sharpness(img).enhance(2.0)
    return np.array(img)


_PARSE_PROMPT = """Del siguiente texto extraído de un recibo colombiano, extrae la información y devuelve SOLO JSON válido:

TEXTO DEL RECIBO:
{text}

JSON esperado:
{{
  "merchant": "nombre del comercio o null",
  "date": "DD/MM/YYYY o null",
  "items": [{{"name": "producto o servicio", "amount": monto_entero}}],
  "total": monto_total_entero,
  "category": "comida|transporte|vivienda|salud|entretenimiento|ropa|servicios|otro"
}}

Reglas:
- Montos como enteros sin puntos ni comas (85000 no "85.000")
- El total está etiquetado TOTAL, VALOR A PAGAR o TOTAL A PAGAR
- Categorías: restaurante/supermercado→comida | gas/agua/luz/internet/telefonía→servicios | arriendo→vivienda | taxi/bus/gasolina→transporte
- Si un campo no aparece usa null"""


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = re.sub(r"[\$\.]", "", value).replace(",", ".").strip()
        try:
            return float(cleaned)
        except ValueError:
            return default
    return default


def _parse_json(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


def _normalize(data: dict) -> dict:
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    data["items"] = [
        {"name": str(i.get("name") or "").strip(), "amount": _to_float(i.get("amount"), 0.0)}
        for i in items
        if isinstance(i, dict) and i.get("name")
    ]
    data.setdefault("category", "otro")
    data.setdefault("merchant", None)
    data.setdefault("date", None)
    data["total"] = _to_float(data.get("total"), 0.0)
    if data["total"] == 0.0 and data["items"]:
        data["total"] = sum(i["amount"] for i in data["items"])
    return data


def _extract_sync(image_b64: str) -> tuple[str, str, dict]:
    # Paso 1: EasyOCR lee el texto de la imagen (determinístico, no LLM)
    img_array = _preprocess(image_b64)
    results = _get_reader().readtext(img_array, detail=0, paragraph=True)
    raw_text = "\n".join(results).strip()

    if not raw_text:
        return raw_text, "", _normalize({})

    # Paso 2: gemma4 estructura el texto en JSON (tarea de texto puro)
    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": _PARSE_PROMPT.format(text=raw_text)}],
        options={"temperature": 0, "num_predict": 512, "num_ctx": 2048},
    )
    raw_json = response["message"]["content"]
    return raw_text, raw_json, _normalize(_parse_json(raw_json))


@tool
def extract_receipt(image_base64: str) -> str:
    """Extrae información estructurada de una foto de recibo o factura.

    Args:
        image_base64: Imagen del recibo codificada en base64.
    """
    _, _, result = _extract_sync(image_base64)
    return json.dumps(result, ensure_ascii=False)


async def extract_receipt_from_image(image_b64: str) -> dict:
    """Async wrapper for FastAPI endpoints."""
    _, _, result = await asyncio.wait_for(asyncio.to_thread(_extract_sync, image_b64), timeout=120)
    return result


async def debug_extract(image_b64: str) -> dict:
    """Retorna pasos intermedios para diagnóstico."""
    raw_text, raw_json, result = await asyncio.wait_for(
        asyncio.to_thread(_extract_sync, image_b64), timeout=120
    )
    return {
        "paso1_easyocr": raw_text,
        "paso2_gemma4_raw": raw_json,
        "resultado_final": result,
    }
