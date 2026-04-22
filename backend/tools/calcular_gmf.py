from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction


@tool
def calcular_gmf(year: int = 0) -> str:
    """Estima el GMF (Gravamen a los Movimientos Financieros — 4×1000) pagado
    en el año y calcula la deducción aplicable en renta.

    El GMF es 0.4% sobre cada movimiento bancario. Como Leaf no distingue si
    una transacción fue en efectivo o por banco, este cálculo usa el total
    de transacciones como estimación. El 50% del GMF pagado es deducible en renta.

    Args:
        year: Año fiscal. Usa 0 para el año en curso.
    """
    if year == 0:
        year = date.today().year

    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    with Session(engine) as session:
        rows = session.exec(
            select(Transaction.type, func.sum(Transaction.amount).label("total"))
            .where(Transaction.date >= str(start))
            .where(Transaction.date < str(end))
            .group_by(Transaction.type)
        ).all()

    by_type = {r[0]: r[1] for r in rows}
    total_expenses = by_type.get("expense", 0)
    total_income = by_type.get("income", 0)
    total_movimientos = total_expenses + total_income

    tasa_gmf = 0.004  # 4 por cada 1.000
    gmf_estimado = total_movimientos * tasa_gmf
    deduccion = gmf_estimado * 0.50  # 50% es deducible en renta

    return (
        f"4️⃣ GMF (4×1000) estimado {year}:\n"
        f"\n"
        f"  Total movimientos registrados: ${total_movimientos:,.0f}\n"
        f"  → Ingresos:  ${total_income:,.0f}\n"
        f"  → Gastos:    ${total_expenses:,.0f}\n"
        f"\n"
        f"  GMF estimado (0.4%):     ${gmf_estimado:,.0f}\n"
        f"  Deducción en renta (50%): ${deduccion:,.0f}\n"
        f"\n"
        "📌 El 50% del GMF pagado se puede descontar en la declaración de renta "
        "(Art. 115 ET). Verifica con los extractos bancarios el GMF real cobrado.\n"
        "⚠️ Estimación — Leaf no tiene acceso a extractos bancarios."
    )
