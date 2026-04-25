import asyncio
import json
import re

import ollama
from langchain_core.tools import tool

from backend.config import settings

_VISION_MODEL = "moondream:latest"

_READ_PROMPT = "Lee y transcribe todo el texto visible en esta imagen de recibo o factura. Incluye comercio, productos, precios y total a pagar."

_PARSE_PROMPT = """Del siguiente texto de un recibo colombiano extrae la información y devuelve SOLO JSON válido, sin texto adicional:

TEXTO:
{text}

Formato esperado:
{{
  "merchant": "nombre del comercio o null",
  "date": "DD/MM/YYYY o null",
  "items": [{{"name": "producto o servicio", "amount": monto_entero}}],
  "total": monto_total_entero,
  "category": "comida|transporte|vivienda|salud|entretenimiento|ropa|servicios|otro"
}}

Reglas:
- Montos como enteros sin puntos ni comas (85000 no "85.000")
- Restaurante/supermercado → comida | Gas/agua/luz/internet → servicios | Arriendo → vivienda | Taxi/bus/gasolina → transporte
- Si un campo no aparece en el texto usa null"""


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


def _extract_sync(image_b64: str) -> dict:
    # Paso 1: Moondream lee el texto de la imagen
    vision = ollama.chat(
        model=_VISION_MODEL,
        messages=[{"role": "user", "content": _READ_PROMPT, "images": [image_b64]}],
        options={"num_predict": 512},
    )
    raw_text = vision["message"]["content"].strip()

    if not raw_text:
        return _normalize({})

    # Paso 2: gemma4 estructura el texto en JSON
    parse = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": _PARSE_PROMPT.format(text=raw_text)}],
        options={"temperature": 0, "num_predict": 512},
    )
    return _normalize(_parse_json(parse["message"]["content"]))


@tool
def extract_receipt(image_base64: str) -> str:
    """Extrae información estructurada de una foto de recibo o factura.

    Args:
        image_base64: Imagen del recibo codificada en base64.
    """
    return json.dumps(_extract_sync(image_base64), ensure_ascii=False)


async def extract_receipt_from_image(image_b64: str) -> dict:
    """Async wrapper for FastAPI endpoints."""
    return await asyncio.wait_for(asyncio.to_thread(_extract_sync, image_b64), timeout=120)
