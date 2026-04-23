"""Importador de facturas electrónicas DIAN (UBL XML) — Colombia."""

import re
from datetime import datetime
from xml.etree import ElementTree as ET

from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType
from backend.tools.csv_importer import _infer_category

# DIAN UBL namespaces
_NS = {
    "fe": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}


def _get_text(element: ET.Element | None, path: str, namespaces: dict) -> str:
    if element is None:
        return ""
    found = element.find(path, namespaces)
    return found.text.strip() if found is not None and found.text else ""


def parse_dian_xml(xml_content: str) -> dict:
    """Parses a DIAN UBL XML invoice and returns structured data."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        return {"error": f"XML inválido: {e}"}

    # Support both Invoice and CreditNote root elements
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    # Date
    issue_date = _get_text(root, "cbc:IssueDate", _NS)
    issue_time = _get_text(root, "cbc:IssueTime", _NS)
    try:
        dt = datetime.strptime(issue_date, "%Y-%m-%d")
    except ValueError:
        dt = datetime.utcnow()

    # Supplier name
    supplier = (
        _get_text(root, ".//cac:AccountingSupplierParty//cbc:RegistrationName", _NS)
        or _get_text(root, ".//cac:AccountingSupplierParty//cbc:Name", _NS)
        or "Proveedor"
    )

    # Total amount
    total_str = (
        _get_text(root, ".//cac:LegalMonetaryTotal/cbc:PayableAmount", _NS)
        or _get_text(root, ".//cbc:LineExtensionAmount", _NS)
        or "0"
    )
    try:
        total = abs(float(total_str))
    except ValueError:
        total = 0.0

    # Invoice number
    invoice_id = _get_text(root, "cbc:ID", _NS) or "N/A"

    # Line items (description for category inference)
    lines = root.findall(".//cac:InvoiceLine/cac:Item/cbc:Description", _NS)
    description = "; ".join(l.text.strip() for l in lines[:3] if l.text) or supplier

    return {
        "date": dt,
        "supplier": supplier,
        "total": total,
        "invoice_id": invoice_id,
        "description": description,
        "tag": tag,
    }


def import_dian_xml_content(xml_content: str) -> dict:
    """Parses and imports a DIAN XML invoice as a transaction."""
    data = parse_dian_xml(xml_content)
    if "error" in data:
        return data

    if data["total"] == 0:
        return {"error": "Monto de la factura es cero — verifica el XML."}

    # CreditNote = expense reduction (still log as expense but note it)
    tx_type = TransactionType.expense

    with Session(engine) as session:
        tx = Transaction(
            amount=data["total"],
            description=f"Factura {data['invoice_id']} — {data['supplier']}"[:200],
            category=_infer_category(data["description"] + " " + data["supplier"]),
            type=tx_type,
            merchant=data["supplier"][:50],
            date=data["date"],
            notes=f"Importada desde e-factura DIAN. ID: {data['invoice_id']}",
        )
        session.add(tx)
        session.commit()
        session.refresh(tx)
        tx_id = tx.id

    return {
        "tx_id": tx_id,
        "supplier": data["supplier"],
        "total": data["total"],
        "invoice_id": data["invoice_id"],
        "date": data["date"].strftime("%Y-%m-%d"),
    }


@tool
def import_dian_factura(xml_content: str) -> str:
    """Importa una factura electrónica DIAN (UBL XML) como transacción de gasto.

    Args:
        xml_content: Contenido del archivo XML de la factura electrónica.
    """
    result = import_dian_xml_content(xml_content)
    if "error" in result:
        return f"❌ Error al importar factura DIAN: {result['error']}"

    return (
        f"✅ Factura DIAN importada\n"
        f"  Proveedor: {result['supplier']}\n"
        f"  Factura N°: {result['invoice_id']}\n"
        f"  Fecha: {result['date']}\n"
        f"  Monto: ${result['total']:,.0f}\n"
        f"  Transacción ID: {result['tx_id']}"
    )
