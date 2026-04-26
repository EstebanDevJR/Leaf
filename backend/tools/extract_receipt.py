import asyncio
import json
import re
from datetime import datetime

import ollama
from langchain_core.tools import tool

from backend.config import settings

# Prompt corto — gemma4 falla con prompts largos en modo visión
_PROMPT = "Read this receipt image and return JSON with merchant, date, items (name + amount as integer), total as integer, and category."

_CATEGORY_MAP = {
    "utilities": "servicios", "utility": "servicios", "services": "servicios",
    "food": "comida", "grocery": "comida", "groceries": "comida", "restaurant": "comida",
    "transport": "transporte", "transportation": "transporte", "travel": "transporte",
    "housing": "vivienda", "rent": "vivienda",
    "health": "salud", "healthcare": "salud", "medical": "salud",
    "entertainment": "entretenimiento",
    "clothing": "ropa", "clothes": "ropa",
    "other": "otro",
}

_VALID_CATEGORIES = {"comida", "transporte", "vivienda", "salud", "entretenimiento", "ropa", "servicios", "otro"}


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return value


def _normalize_category(value: str | None) -> str:
    if not value:
        return "otro"
    lower = value.lower().strip()
    if lower in _VALID_CATEGORIES:
        return lower
    return _CATEGORY_MAP.get(lower, "otro")


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
    data["category"] = _normalize_category(data.get("category"))
    data["date"] = _normalize_date(data.get("date"))
    data.setdefault("merchant", None)
    data["total"] = _to_float(data.get("total"), 0.0)
    if data["total"] == 0.0 and data["items"]:
        data["total"] = sum(i["amount"] for i in data["items"])
    return data


def _extract_sync(image_b64: str) -> tuple[str, dict]:
    # Un solo paso — prompt corto, sin temperature, num_predict alto
    response = ollama.chat(
        model=settings.ollama_vision_model,
        messages=[{"role": "user", "content": _PROMPT, "images": [image_b64]}],
        options={"num_predict": 1024},
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
    return {"raw_response": raw, "resultado_final": result}
