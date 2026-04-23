"""Rutas de importación (CSV, DIAN XML) y exportación (PDF, Excel)."""

from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()


# ── Import ────────────────────────────────────────────────────────────────────

class CSVImportResult(BaseModel):
    imported: int
    expenses: int
    incomes: int
    bank: str


@router.post("/csv", response_model=CSVImportResult)
async def import_csv(file: UploadFile, bank: str):
    """Importa transacciones desde un CSV de banco colombiano.

    Bancos soportados: bancolombia, davivienda, nequi, nubank, daviplata.
    """
    from backend.tools.csv_importer import import_csv_content

    content = (await file.read()).decode("utf-8-sig", errors="replace")
    result = import_csv_content(content, bank)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return CSVImportResult(**result)


class DianXMLImportResult(BaseModel):
    tx_id: int
    supplier: str
    total: float
    invoice_id: str
    date: str


@router.post("/dian-factura", response_model=DianXMLImportResult)
async def import_dian_xml(file: UploadFile):
    """Importa una factura electrónica DIAN (UBL XML) como transacción de gasto."""
    from backend.tools.dian_factura import import_dian_xml_content

    content = (await file.read()).decode("utf-8", errors="replace")
    result = import_dian_xml_content(content)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])
    return DianXMLImportResult(**result)


# ── Export ────────────────────────────────────────────────────────────────────

@router.get("/excel")
def export_excel(year: int = 0, month: int = 0):
    """Exporta transacciones del mes a Excel (.xlsx)."""
    from backend.tools.export_tools import export_excel as _export

    today = date.today()
    y, m = year or today.year, month or today.month
    try:
        data = _export(y, m)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="openpyxl no instalado. Ejecuta: uv add openpyxl",
        )
    filename = f"leaf_{y}_{m:02d}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
def export_pdf(year: int = 0, month: int = 0, mode: str = "standard"):
    """Exporta reporte mensual a PDF. mode=standard|contador."""
    from backend.tools.export_tools import export_pdf as _export

    today = date.today()
    y, m = year or today.year, month or today.month
    try:
        data = _export(y, m, mode)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="fpdf2 no instalado. Ejecuta: uv add fpdf2",
        )
    filename = f"leaf_{y}_{m:02d}{'_contador' if mode == 'contador' else ''}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
