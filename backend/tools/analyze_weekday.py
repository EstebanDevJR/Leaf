from collections import defaultdict
from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType

DAYS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


@tool
def analyze_weekday(period_days: int = 30, category: str = "all") -> str:
    """Analiza la distribución de gastos por día de la semana.

    Args:
        period_days: Período a analizar en días (default 30).
        category: Categoría específica o "all" para todas.
    """
    today = date.today()
    start = today - timedelta(days=period_days)

    with Session(engine) as session:
        q = (
            select(Transaction)
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(start))
        )
        if category != "all":
            q = q.where(Transaction.category == category)
        txs = session.exec(q).all()

    if not txs:
        return f"Sin gastos en los últimos {period_days} días."

    totals: dict[int, float] = defaultdict(float)
    counts: dict[int, int] = defaultdict(int)

    for tx in txs:
        day = tx.date.weekday()  # 0=Monday … 6=Sunday
        totals[day] += tx.amount
        counts[day] += 1

    total_all = sum(totals.values())
    max_day = max(totals, key=lambda d: totals[d])
    min_day = min(totals, key=lambda d: totals[d])

    lines = [f"📅 Gastos por día de semana — últimos {period_days} días:\n"]
    for day in range(7):
        amount = totals.get(day, 0)
        count = counts.get(day, 0)
        pct = amount / total_all * 100 if total_all > 0 else 0
        bar = "█" * int(pct / 5)
        marker = " 🔝" if day == max_day else " 🟢" if day == min_day else ""
        lines.append(
            f"  {DAYS_ES[day]:<10} ${amount:>10,.0f}  {pct:4.1f}%  {bar}{marker}"
        )

    avg_day = total_all / 7
    lines.append(f"\nPromedio/día: ${avg_day:,.0f}")
    lines.append(
        f"Día más caro: {DAYS_ES[max_day]} (${totals[max_day]:,.0f}, "
        f"{totals[max_day]/avg_day:.1f}x el promedio)"
    )
    if max_day in (4, 5):  # Friday or Saturday
        lines.append("Tip: Los gastos de ocio suelen concentrarse en fin de semana.")

    return "\n".join(lines)
