import asyncio
import json
import re

import ollama
from langchain_core.tools import tool

from backend.config import settings

_PROMPT = """Look at this receipt image. Extract the information and return ONLY this JSON, no other text:
{
  "merchant": "store name as shown, or null",
  "date": "DD/MM/YYYY or null",
  "items": [{"name": "item name", "amount": integer_amount}],
  "total": integer_total,
  "category": "comida|transporte|vivienda|salud|entretenimiento|ropa|servicios|otro"
}

Rules: amounts as plain integers (85000 not "85.000"). Total is labeled TOTAL or VALOR A PAGAR.
Categories: restaurant/supermarket=comida, gas/water/electricity/internet=servicios, rent=vivienda, taxi/bus/fuel=transporte."""


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


def _extract_sync(image_b64: str) -> tuple[str, dict]:
    response = ollama.chat(
        model=settings.ollama_vision_model,
        messages=[{"role": "user", "content": _PROMPT, "images": [image_b64]}],
        options={"temperature": 0, "num_predict": 512, "num_ctx": 2048},
    )
    raw = response["message"]["content"]
    return raw, _normalize(_parse_json(raw))


@tool
def extract_receipt(image_base64: str) -> str:
    """Extrae información estructurada de una foto de recibo o factura.

    Args:
        image_base64: Imagen del recibo codificada en base64.
    """
    _, result = _extract_sync(image_base64)
    return json.dumps(result, ensure_ascii=False)


async def extract_receipt_from_image(image_b64: str) -> dict:
    """Async wrapper for FastAPI endpoints."""
    _, result = await asyncio.wait_for(asyncio.to_thread(_extract_sync, image_b64), timeout=120)
    return result


async def debug_extract(image_b64: str) -> dict:
    """Retorna pasos intermedios para diagnóstico."""
    raw, result = await asyncio.wait_for(asyncio.to_thread(_extract_sync, image_b64), timeout=120)
    return {"modelo": settings.ollama_vision_model, "raw_response": raw, "resultado_final": result}
