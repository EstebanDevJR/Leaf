from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType

# UVT values (Unidad de Valor Tributario)
UVT_BY_YEAR: dict[int, float] = {
    2023: 42412,
    2024: 47065,
    2025: 49799,
}

# Colombian income tax brackets (in UVT, for natural persons, cedula general)
# Format: (upper_bound_uvt, marginal_rate)
RENTA_BRACKETS = [
    (1090, 0.00),
    (1700, 0.19),
    (4100, 0.28),
    (8670, 0.33),
    (18970, 0.35),
    (31000, 0.37),
    (float("inf"), 0.39),
]


def _tax_from_uvt(net_uvt: float) -> float:
    tax = 0.0
    prev = 0.0
    for upper, rate in RENTA_BRACKETS:
        if net_uvt <= prev:
            break
        taxable = min(net_uvt, upper) - prev
        tax += taxable * rate
        prev = upper
    return tax


@tool
def calculate_renta(year: int = 0) -> str:
    """Calcula el impuesto de renta estimado para Colombia basado en los ingresos
    registrados en Leaf. El resultado es una estimación orientativa.

    Args:
        year: Año fiscal (ej. 2024). Usa 0 para el año en curso.
    """
    if year == 0:
        year = date.today().year

    uvt = UVT_BY_YEAR.get(year, UVT_BY_YEAR[max(UVT_BY_YEAR)])
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
            ).one()
            or 0
        )

    # 25% deduction for independientes, capped at 2880 UVT (Art. 206 ET)
    deduction = min(total_income * 0.25, 2880 * uvt)
    net_income = max(0.0, total_income - deduction)
    net_uvt = net_income / uvt

    tax_uvt = _tax_from_uvt(net_uvt)
    tax_cop = tax_uvt * uvt
    effective_rate = (tax_cop / total_income * 100) if total_income > 0 else 0.0

    # Threshold to declare: gross income > 1400 UVT (2024 onward)
    declare_threshold = 1400 * uvt
    must_declare = total_income > declare_threshold

    return (
        f"📋 Estimación Renta {year}:\n"
        f"  Ingresos brutos:    ${total_income:,.0f}\n"
        f"  Deducción (25%):    ${deduction:,.0f}\n"
        f"  Renta líquida:      ${net_income:,.0f} ({net_uvt:.0f} UVT)\n"
        f"  Impuesto estimado:  ${tax_cop:,.0f} ({effective_rate:.1f}% tasa efectiva)\n"
        f"  UVT {year}:         ${uvt:,}\n"
        f"\n"
        + (
            "⚠️ Estás obligado a declarar renta (ingresos > 1400 UVT)."
            if must_declare
            else "✅ Posiblemente no estás obligado a declarar (ingresos < 1400 UVT)."
        )
        + "\n⚠️ Esta es una estimación. Consulta a un contador para tu declaración oficial."
    )
