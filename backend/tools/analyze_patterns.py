from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def analyze_patterns(category: str = "all", period_days: int = 30) -> str:
    """Analiza tendencias de gasto por categoría comparando el período actual con el anterior.

    Args:
        category: Categoría a analizar o "all" para todas.
        period_days: Duración del período en días (default 30).
    """
    today = date.today()
    period_start = today - timedelta(days=period_days)
    prev_start = period_start - timedelta(days=period_days)

    with Session(engine) as session:
        def _totals(start: date, end: date) -> dict[str, float]:
            q = (
                select(Transaction.category, func.sum(Transaction.amount).label("t"))
                .where(Transaction.type == TransactionType.expense)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
                .group_by(Transaction.category)
            )
            if category != "all":
                q = q.where(Transaction.category == category)
            return {row[0]: row[1] for row in session.exec(q).all()}

        current = _totals(period_start, today)
        previous = _totals(prev_start, period_start)

    if not current:
        return f"Sin gastos registrados en los últimos {period_days} días."

    lines = [f"📊 Análisis de patrones — últimos {period_days} días vs período anterior:\n"]
    for cat, total in sorted(current.items(), key=lambda x: -x[1]):
        prev = previous.get(cat, 0)
        if prev > 0:
            delta = (total - prev) / prev * 100
            arrow = "🔴 +" if delta > 20 else "🟢 " if delta < -10 else "➡️  "
            change = f"{arrow}{delta:+.0f}% (antes ${prev:,.0f})"
        else:
            change = "🆕 nuevo período"
        lines.append(f"  {cat}: ${total:,.0f} — {change}")

    total_current = sum(current.values())
    total_prev = sum(previous.values())
    if total_prev > 0:
        delta_total = (total_current - total_prev) / total_prev * 100
        lines.append(f"\nTotal: ${total_current:,.0f} ({delta_total:+.0f}% vs período anterior)")
    else:
        lines.append(f"\nTotal: ${total_current:,.0f}")

    return "\n".join(lines)
