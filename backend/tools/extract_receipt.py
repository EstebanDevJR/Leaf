import asyncio
import json
import re

import ollama
from langchain_core.tools import tool

from backend.config import settings

# Prompt simple — gemma4 falla con prompts complejos en modo visión
_READ_PROMPT = "Read all text visible in this image exactly as it appears. Include all numbers, prices and names."

_PARSE_PROMPT = """Extract merchant, date, total and items from this Colombian receipt text. Return only JSON.

{text}

JSON format:
{{
  "merchant": "store name or null",
  "date": "DD/MM/YYYY or null",
  "items": [{{"name": "item", "amount": integer}}],
  "total": integer_no_dots,
  "category": "comida|transporte|vivienda|salud|entretenimiento|ropa|servicios|otro"
}}

Category rules: restaurant/supermarket=comida, gas/water/electricity/internet=servicios, rent=vivienda, taxi/bus/fuel=transporte."""


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
    # Paso 1: gemma4 lee el texto de la imagen con prompt simple
    # IMPORTANTE: no setear temperature — gemma4:e4b falla con temperature explícito
    r1 = ollama.chat(
        model=settings.ollama_vision_model,
        messages=[{"role": "user", "content": _READ_PROMPT, "images": [image_b64]}],
        options={"num_predict": 512},
    )
    raw_text = r1["message"]["content"].strip()

    if not raw_text:
        return raw_text, "", _normalize({})

    # Paso 2: gemma4 estructura el texto en JSON (sin imagen, sin temperature)
    # num_predict >= 512 es necesario — valores menores devuelven respuesta vacía
    r2 = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": _PARSE_PROMPT.format(text=raw_text)}],
        options={"num_predict": 1024},
    )
    raw_json = r2["message"]["content"]
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
        "paso1_texto_leido": raw_text,
        "paso2_json_crudo": raw_json,
        "resultado_final": result,
    }
