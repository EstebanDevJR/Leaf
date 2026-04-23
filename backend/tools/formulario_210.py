"""Generador del Formulario 210 de renta para personas naturales — Colombia."""

from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType
from backend.tools.get_uvt import get_uvt

# Tarifas progresivas renta natural 2025 (rangos en UVT)
BRACKETS_2025 = [
    (0, 1090, 0.0, 0),
    (1090, 1700, 0.19, 1090),
    (1700, 4100, 0.28, 1700),
    (4100, 8670, 0.33, 4100),
    (8670, 18970, 0.35, 8670),
    (18970, 31000, 0.37, 18970),
    (31000, float("inf"), 0.39, 31000),
]

ADICIONAL_BRACKETS = [
    (0, 300, 0.0, 0),
    (300, float("inf"), 0.15, 300),
]


def _calc_tax(renta_uvt: float, brackets: list) -> float:
    impuesto = 0.0
    for low, high, rate, base in brackets:
        if renta_uvt <= low:
            break
        tramo = min(renta_uvt, high) - max(low, base)
        if tramo > 0:
            impuesto += tramo * rate
    return impuesto


@tool
def formulario_210(year: int = 0) -> str:
    """Genera una declaración de renta preliminar estructurada según el Formulario 210 (persona natural).

    Args:
        year: Año fiscal a declarar (0 = año en curso).
    """
    today = date.today()
    fiscal_year = year if year > 0 else today.year - 1 if today.month < 8 else today.year
    uvt = get_uvt(fiscal_year)

    start = date(fiscal_year, 1, 1)
    end = date(fiscal_year + 1, 1, 1)

    with Session(engine) as session:
        # Casilla 42 — Ingresos brutos
        ingresos_brutos = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
            ).one() or 0
        )

        # Casilla 55 — Total gastos (para depuración)
        total_gastos = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.expense)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
            ).one() or 0
        )

        # GMF pagado (casilla 87) — estimado 0.4%
        gmf_pagado = total_gastos * 0.004
        gmf_deducible = gmf_pagado * 0.5  # 50% deducible

        # Costos y gastos laborales — 25% de ingresos, tope 2880 UVT
        deduccion_independiente = min(ingresos_brutos * 0.25, 2880 * uvt)

    # Renta líquida gravable
    renta_liquida = max(0, ingresos_brutos - deduccion_independiente - gmf_deducible)
    renta_liquida_uvt = renta_liquida / uvt

    # Impuesto ordinario (casilla 89)
    impuesto_uvt = _calc_tax(renta_liquida_uvt, BRACKETS_2025)
    impuesto_cop = impuesto_uvt * uvt

    # Impuesto adicional ganancias ocasionales (simplificado — 0 si no hay)
    impuesto_adicional = 0.0

    total_impuesto = impuesto_cop + impuesto_adicional
    obligado = ingresos_brutos > 1400 * uvt

    lines = [
        f"📋 FORMULARIO 210 — Declaración de Renta {fiscal_year}",
        f"   Persona Natural No Residente / Empleado / Independiente",
        f"   UVT {fiscal_year}: ${uvt:,.0f}",
        "",
        "═" * 55,
        "SECCIÓN I — PATRIMONIO",
        "  Casilla 28-35: Actualizar manualmente con bienes y deudas",
        "",
        "SECCIÓN II — INGRESOS",
        f"  Casilla 42 — Ingresos brutos:              ${ingresos_brutos:,.0f}",
        f"              ({ingresos_brutos/uvt:.1f} UVT)",
        "",
        "SECCIÓN III — COSTOS Y DEDUCCIONES",
        f"  Casilla 60 — Deducción independiente 25%:  ${deduccion_independiente:,.0f}",
        f"              (tope 2.880 UVT = ${2880*uvt:,.0f})",
        f"  Casilla 87 — GMF deducible (50%):           ${gmf_deducible:,.0f}",
        f"  Total deducciones:                          ${deduccion_independiente + gmf_deducible:,.0f}",
        "",
        "SECCIÓN IV — RENTA LÍQUIDA",
        f"  Casilla 78 — Renta líquida:                ${renta_liquida:,.0f}",
        f"              ({renta_liquida_uvt:.1f} UVT)",
        "",
        "SECCIÓN V — IMPUESTO",
        f"  Casilla 89 — Impuesto renta ordinario:     ${impuesto_cop:,.0f}",
        f"  Casilla 95 — Impuesto complementario:      ${impuesto_adicional:,.0f}",
        f"  Casilla 97 — Total impuesto a cargo:       ${total_impuesto:,.0f}",
        "",
        "═" * 55,
        f"  ¿Obligado a declarar? {'SÍ ✅' if obligado else 'NO (ingresos < 1.400 UVT) ℹ️'}",
        "",
        "⚠️  Este formulario es preliminar y educativo.",
        "    Presenta y firma con un contador público certificado.",
        "    Los valores de patrimonio y algunas deducciones deben",
        "    actualizarse manualmente con tu documentación real.",
    ]
    return "\n".join(lines)
