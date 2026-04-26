import asyncio
import json
import re
from datetime import datetime

import ollama
from langchain_core.tools import tool

from backend.config import settings

_SCHEMA = {
    "type": "object",
    "properties": {
        "merchant": {"type": "string"},
        "date":     {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name":   {"type": "string"},
                    "amount": {"type": "integer"},
                },
                "required": ["name", "amount"],
            },
        },
        "total":    {"type": "integer"},
        "category": {
            "type": "string",
            "enum": ["comida", "transporte", "vivienda", "salud",
                     "entretenimiento", "ropa", "servicios", "otro"],
        },
    },
    "required": ["merchant", "date", "items", "total", "category"],
}

_PROMPT = "Extract merchant, date (DD/MM/YYYY), items with integer amounts, the final amount to pay (TOTAL A PAGAR / VALOR A PAGAR / GRAN TOTAL — never subtotal or IVA), and category from this receipt."


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return value


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


def _normalize(data: dict) -> dict:
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    data["items"] = [
        {"name": str(i.get("name") or "").strip(), "amount": _to_float(i.get("amount"), 0.0)}
        for i in items
        if isinstance(i, dict) and i.get("name")
    ]
    data["date"] = _normalize_date(data.get("date"))
    if not data.get("merchant"):
        data["merchant"] = None
    if data.get("category") not in {"comida", "transporte", "vivienda", "salud",
                                     "entretenimiento", "ropa", "servicios", "otro"}:
        data["category"] = "otro"
    data["total"] = _to_float(data.get("total"), 0.0)
    if data["total"] == 0.0 and data["items"]:
        data["total"] = sum(i["amount"] for i in data["items"])
    return data


def _extract_sync(image_b64: str) -> tuple[str, dict]:
    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": _PROMPT, "images": [image_b64]}],
        format=_SCHEMA,
        options={"num_predict": 1024},
    )
    raw = response["message"]["content"]
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {}
    return raw, _normalize(data)


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
