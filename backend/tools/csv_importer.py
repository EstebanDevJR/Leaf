"""Importador masivo de CSV de bancos colombianos: Bancolombia, Davivienda, Nequi, Nubank, Daviplata."""

import csv
import io
from datetime import datetime
from typing import Any

from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType

# ── Category inference by keyword ────────────────────────────────────────────

_KEYWORD_MAP = {
    "comida": ["restaurante", "comida", "cafe", "mcdonald", "burger", "pizza", "rappi", "ifood",
               "uber eats", "domino", "subway", "kfc", "pollo", "almuerzo", "desayuno"],
    "transporte": ["uber", "cabify", "didi", "taxi", "transmilenio", "sitp", "bus", "metro",
                   "gasolina", "parqueadero", "peaje", "tren", "transporte"],
    "vivienda": ["arriendo", "renta", "administracion", "gas", "acueducto", "epm", "codensa",
                 "energia", "agua", "internet", "claro", "movistar", "tigo", "etb"],
    "salud": ["farmacia", "drogueria", "medico", "clinica", "hospital", "medicina", "salud",
              "laboratorio", "odontologia", "dentista", "gym", "gimnasio"],
    "entretenimiento": ["cine", "streaming", "netflix", "spotify", "prime", "disney", "hbo",
                        "youtube", "gaming", "juego", "bar", "discoteca", "fiesta", "concierto"],
    "ropa": ["zara", "h&m", "adidas", "nike", "falabella", "exito", "alkosto", "ropa",
             "zapatos", "calzado", "vestuario"],
    "servicios": ["banco", "transferencia", "servicio", "impuesto", "seguro", "dian"],
}


def _infer_category(description: str) -> str:
    desc_lower = description.lower()
    for category, keywords in _KEYWORD_MAP.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "otro"


def _parse_amount(value: str) -> float:
    cleaned = value.replace("$", "").replace(",", "").replace(".", "").replace(" ", "").strip()
    # Handle Colombian format: 1.234.567,89 → 1234567.89
    if "," in value and "." in value:
        # Assume last comma is decimal separator
        cleaned = value.replace("$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return abs(float(cleaned))
    except ValueError:
        return 0.0


def _parse_date(value: str) -> datetime:
    formats = [
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y",
        "%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
        "%d %b %Y", "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return datetime.utcnow()


# ── Bank-specific parsers ─────────────────────────────────────────────────────

def _parse_bancolombia(reader: list[dict]) -> list[dict[str, Any]]:
    """Formato Bancolombia: Fecha, Descripción, Oficina, Referencia, Valor, Saldo"""
    txs = []
    for row in reader:
        amount = _parse_amount(row.get("Valor", row.get("valor", "0")))
        if amount == 0:
            continue
        desc = row.get("Descripción", row.get("Descripcion", row.get("descripcion", "")))
        raw_date = row.get("Fecha", row.get("fecha", ""))
        # Bancolombia: positive = income, negative = expense (already handled by abs)
        raw_val = row.get("Valor", row.get("valor", "0")).strip()
        tx_type = TransactionType.income if not raw_val.startswith("-") else TransactionType.expense
        txs.append({
            "amount": amount, "description": desc,
            "category": _infer_category(desc), "type": tx_type,
            "date": _parse_date(raw_date), "merchant": desc[:50],
        })
    return txs


def _parse_davivienda(reader: list[dict]) -> list[dict[str, Any]]:
    """Formato Davivienda: Fecha, Concepto, Débito, Crédito, Saldo"""
    txs = []
    for row in reader:
        debito = _parse_amount(row.get("Débito", row.get("Debito", "0")))
        credito = _parse_amount(row.get("Crédito", row.get("Credito", "0")))
        if debito == 0 and credito == 0:
            continue
        desc = row.get("Concepto", row.get("concepto", ""))
        raw_date = row.get("Fecha", row.get("fecha", ""))
        if debito > 0:
            txs.append({"amount": debito, "description": desc, "category": _infer_category(desc),
                        "type": TransactionType.expense, "date": _parse_date(raw_date), "merchant": desc[:50]})
        if credito > 0:
            txs.append({"amount": credito, "description": desc, "category": _infer_category(desc),
                        "type": TransactionType.income, "date": _parse_date(raw_date), "merchant": desc[:50]})
    return txs


def _parse_nequi(reader: list[dict]) -> list[dict[str, Any]]:
    """Formato Nequi: Fecha, Descripción, Monto, Tipo"""
    txs = []
    for row in reader:
        amount = _parse_amount(row.get("Monto", row.get("monto", "0")))
        if amount == 0:
            continue
        desc = row.get("Descripción", row.get("Descripcion", row.get("descripcion", "")))
        raw_date = row.get("Fecha", row.get("fecha", ""))
        tipo = row.get("Tipo", row.get("tipo", "")).lower()
        tx_type = TransactionType.income if "recibido" in tipo or "ingreso" in tipo else TransactionType.expense
        txs.append({"amount": amount, "description": desc, "category": _infer_category(desc),
                    "type": tx_type, "date": _parse_date(raw_date), "merchant": desc[:50]})
    return txs


def _parse_nubank(reader: list[dict]) -> list[dict[str, Any]]:
    """Formato Nubank: date, title, amount"""
    txs = []
    for row in reader:
        amount = _parse_amount(row.get("amount", row.get("monto", "0")))
        if amount == 0:
            continue
        desc = row.get("title", row.get("description", row.get("descripcion", "")))
        raw_date = row.get("date", row.get("fecha", ""))
        # Nubank: positive = expense (credit card charge)
        raw_val = str(row.get("amount", "0")).strip()
        tx_type = TransactionType.income if raw_val.startswith("-") else TransactionType.expense
        txs.append({"amount": amount, "description": desc, "category": _infer_category(desc),
                    "type": tx_type, "date": _parse_date(raw_date), "merchant": desc[:50]})
    return txs


def _parse_daviplata(reader: list[dict]) -> list[dict[str, Any]]:
    """Formato Daviplata: Fecha, Transacción, Monto, Estado"""
    txs = []
    for row in reader:
        amount = _parse_amount(row.get("Monto", row.get("monto", row.get("Valor", "0"))))
        if amount == 0:
            continue
        desc = row.get("Transacción", row.get("Transaccion", row.get("transaccion", "")))
        raw_date = row.get("Fecha", row.get("fecha", ""))
        estado = row.get("Estado", "").lower()
        if estado and "fallida" in estado:
            continue
        desc_lower = desc.lower()
        tx_type = (TransactionType.income
                   if any(w in desc_lower for w in ["recibido", "recarga", "ingreso", "consignacion"])
                   else TransactionType.expense)
        txs.append({"amount": amount, "description": desc, "category": _infer_category(desc),
                    "type": tx_type, "date": _parse_date(raw_date), "merchant": desc[:50]})
    return txs


_BANK_PARSERS = {
    "bancolombia": _parse_bancolombia,
    "davivienda": _parse_davivienda,
    "nequi": _parse_nequi,
    "nubank": _parse_nubank,
    "daviplata": _parse_daviplata,
}


def import_csv_content(csv_content: str, bank: str, profile_id: str = "default") -> dict:
    """Parses CSV content and imports transactions. Returns summary dict."""
    bank_key = bank.lower().strip()
    if bank_key not in _BANK_PARSERS:
        return {"error": f"Banco '{bank}' no soportado. Opciones: {', '.join(_BANK_PARSERS.keys())}"}

    reader = list(csv.DictReader(io.StringIO(csv_content)))
    if not reader:
        return {"error": "CSV vacío o sin encabezados reconocibles."}

    raw_txs = _BANK_PARSERS[bank_key](reader)
    if not raw_txs:
        return {"error": "No se encontraron transacciones válidas en el archivo."}

    imported = 0
    with Session(engine) as session:
        for tx_data in raw_txs:
            tx = Transaction(
                amount=tx_data["amount"],
                description=tx_data["description"][:200],
                category=tx_data["category"],
                type=tx_data["type"],
                merchant=tx_data.get("merchant"),
                date=tx_data["date"],
            )
            session.add(tx)
            imported += 1
        session.commit()

    expenses = sum(1 for t in raw_txs if t["type"] == TransactionType.expense)
    incomes = sum(1 for t in raw_txs if t["type"] == TransactionType.income)
    return {"imported": imported, "expenses": expenses, "incomes": incomes, "bank": bank}


@tool
def import_bank_csv(csv_content: str, bank: str) -> str:
    """Importa transacciones desde el CSV de un banco colombiano.

    Args:
        csv_content: Contenido del archivo CSV como texto.
        bank: Nombre del banco (bancolombia, davivienda, nequi, nubank, daviplata).
    """
    result = import_csv_content(csv_content, bank)
    if "error" in result:
        return f"❌ Error: {result['error']}"
    return (
        f"✅ Importación completada desde {result['bank'].title()}\n"
        f"  Total importadas: {result['imported']} transacciones\n"
        f"  Gastos: {result['expenses']}  |  Ingresos: {result['incomes']}\n"
        "Las categorías se asignaron automáticamente. Revisa y edita si es necesario."
    )
