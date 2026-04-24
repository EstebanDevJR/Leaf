import asyncio
import json
import re

import ollama
from langchain_core.tools import tool

from backend.config import settings

# Single-pass prompt: one call to a vision-capable model does OCR + JSON extraction
_PROMPT = """Lee el texto de esta imagen de recibo o factura colombiana con mucho cuidado.

Primero identifica: nombre del comercio, fecha, cada producto/servicio con su valor, y el total a pagar.

Luego responde SOLO con este JSON (sin texto antes ni después):
{
  "merchant": "nombre exacto del comercio tal como aparece en el recibo, o null",
  "date": "fecha en formato DD/MM/YYYY o null",
  "items": [{"name": "nombre del producto o servicio", "amount": valor_numerico_entero}],
  "total": valor_total_entero_sin_puntos_ni_signos,
  "category": "comida|transporte|vivienda|salud|entretenimiento|ropa|servicios|otro"
}

Reglas de categoría:
- Restaurante, supermercado, tienda de alimentos → "comida"
- Gas, agua, electricidad, internet, telefonía → "servicios"
- Arriendo, administración → "vivienda"
- Taxi, bus, gasolina, peaje → "transporte"

Reglas de montos:
- El total es el valor etiquetado "TOTAL", "VALOR A PAGAR" o "TOTAL A PAGAR"
- Escribe los montos como enteros sin puntos ni comas (85000 no "85.000")
- Si no puedes leer un valor con certeza, usa null"""


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
    """Single Ollama call: main model does vision + JSON extraction."""
    response = ollama.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": _PROMPT, "images": [image_b64]}],
        options={"temperature": 0, "num_predict": 512},
    )
    return _normalize(_parse_json(response["message"]["content"]))


# ── Public API ────────────────────────────────────────────────────────────────

@tool
def extract_receipt(image_base64: str) -> str:
    """Extrae información estructurada de una foto de recibo o factura.

    Args:
        image_base64: Imagen del recibo codificada en base64.
    """
    return json.dumps(_extract_sync(image_base64), ensure_ascii=False)


async def extract_receipt_from_image(image_b64: str) -> dict:
    """Async wrapper for FastAPI endpoints."""
    return await asyncio.wait_for(asyncio.to_thread(_extract_sync, image_b64), timeout=60)
