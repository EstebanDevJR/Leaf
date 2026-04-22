"""Agente DIAN — cálculo de renta, retenciones, GMF, deducciones y fechas tributarias."""

from backend.tools.calculate_renta import calculate_renta
from backend.tools.calcular_deducciones import calcular_deducciones
from backend.tools.calcular_gmf import calcular_gmf
from backend.tools.calcular_retencion import calcular_retencion
from backend.tools.check_deadlines import check_deadlines
from backend.tools.check_obligacion import check_obligacion
from backend.tools.generate_report import generate_report
from backend.tools.generar_borrador import generar_borrador
from backend.tools.get_uvt import get_uvt_vigente

DIAN_TOOLS = [
    check_obligacion,
    calculate_renta,
    calcular_retencion,
    calcular_gmf,
    calcular_deducciones,
    generar_borrador,
    get_uvt_vigente,
    check_deadlines,
    generate_report,
]
