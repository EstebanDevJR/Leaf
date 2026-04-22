from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType
from backend.tools.get_uvt import get_uvt

# DIAN 2025 renta — fechas límite por último dígito NIT
FECHAS_2025 = {
    "0": "2026-04-09", "1": "2026-04-14", "2": "2026-04-16",
    "3": "2026-04-21", "4": "2026-04-23", "5": "2026-04-28",
    "6": "2026-04-30", "7": "2026-05-06", "8": "2026-05-08",
    "9": "2026-05-13",
}

# Income tax brackets (UVT) for natural persons — cedula general
BRACKETS = [
    (1090, 0.00), (1700, 0.19), (4100, 0.28),
    (8670, 0.33), (18970, 0.35), (31000, 0.37), (float("inf"), 0.39),
]


def _tax(net_uvt: float) -> float:
    tax, prev = 0.0, 0.0
    for upper, rate in BRACKETS:
        if net_uvt <= prev:
            break
        tax += (min(net_uvt, upper) - prev) * rate
        prev = upper
    return tax


@tool
def generar_borrador(year: int = 0, nit_sufijo: str = "") -> str:
    """Genera un borrador estructurado de la declaración de renta con todos los
    datos disponibles en Leaf. Útil para revisar con un contador o como resumen
    personal antes de presentar en dian.gov.co.

    Args:
        year: Año fiscal a declarar. Usa 0 para el año anterior (año a declarar).
        nit_sufijo: Último dígito de tu cédula/NIT para calcular fecha límite.
    """
    today = date.today()
    if year == 0:
        # Default: declare previous year (most common case when filing)
        year = today.year - 1 if today.month < 6 else today.year

    uvt = get_uvt(year)
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    with Session(engine) as session:
        # Income
        income_rows = session.exec(
            select(Transaction.category, func.sum(Transaction.amount).label("total"))
            .where(Transaction.type == TransactionType.income)
            .where(Transaction.date >= str(start))
            .where(Transaction.date < str(end))
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()

        # Expenses
        expense_rows = session.exec(
            select(Transaction.category, func.sum(Transaction.amount).label("total"))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(start))
            .where(Transaction.date < str(end))
            .group_by(Transaction.category)
            .order_by(func.sum(Transaction.amount).desc())
        ).all()

        tx_count = (
            session.exec(
                select(func.count(Transaction.id))
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
            ).one()
            or 0
        )

    total_income = sum(r[1] for r in income_rows)
    total_expenses = sum(r[1] for r in expense_rows)

    # Tax calculation
    deduction = min(total_income * 0.25, 2880 * uvt)
    net_income = max(0.0, total_income - deduction)
    net_uvt = net_income / uvt
    tax_uvt = _tax(net_uvt)
    tax_cop = tax_uvt * uvt
    effective_rate = (tax_cop / total_income * 100) if total_income > 0 else 0

    # Declaration obligation
    must_declare = total_income > (1_400 * uvt)

    # Deadline
    deadline_line = ""
    if nit_sufijo:
        digito = nit_sufijo.strip()[-1]
        fecha_str = FECHAS_2025.get(digito)
        if fecha_str:
            d = date.fromisoformat(fecha_str)
            days = (d - today).days
            deadline_line = f"\n📅 Fecha límite (NIT …{digito}): {d.strftime('%d de %B de %Y')} — {days}d\n"

    separator = "─" * 40
    lines = [
        f"📋 BORRADOR DECLARACIÓN DE RENTA {year}",
        f"   Generado por Leaf 🌿 — {today.isoformat()}",
        separator,
        "",
        "1. INGRESOS BRUTOS",
        f"   Total ingresos:    ${total_income:,.0f}",
    ]
    for cat, amt in income_rows:
        lines.append(f"   · {cat:<18} ${amt:,.0f}")

    lines += [
        "",
        "2. COSTOS Y DEDUCCIONES",
        f"   Renta exenta 25%:  ${deduction:,.0f}  (máx 2.880 UVT)",
        f"   Total deducciones: ${deduction:,.0f}",
        "",
        "3. RENTA LÍQUIDA GRAVABLE",
        f"   Renta líquida:     ${net_income:,.0f}",
        f"   En UVT:            {net_uvt:.0f} UVT  (1 UVT = ${uvt:,})",
        "",
        "4. IMPUESTO",
        f"   Impuesto estimado: ${tax_cop:,.0f}",
        f"   Tasa efectiva:     {effective_rate:.1f}%",
        "",
        "5. GASTOS DEL AÑO (referencia)",
        f"   Total gastos:      ${total_expenses:,.0f}  ({tx_count} transacciones)",
    ]
    for cat, amt in expense_rows[:5]:
        lines.append(f"   · {cat:<18} ${amt:,.0f}")

    lines += [
        "",
        separator,
        f"OBLIGADO A DECLARAR: {'⚠️ SÍ' if must_declare else '✅ NO (ingresos < 1.400 UVT)'}",
        deadline_line,
        separator,
        "",
        "⚠️ Este borrador es orientativo. No equivale a la declaración oficial.",
        "   Preséntala en: dian.gov.co → Servicios en línea → Declaraciones",
        "   Recomendado: revisar con un contador antes de presentar.",
    ]
    return "\n".join(lines)
