from collections import defaultdict
from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def find_subscriptions(period_days: int = 90) -> str:
    """Identifica pagos recurrentes y posibles suscripciones activas.

    Args:
        period_days: Período a analizar en días (default 90).
    """
    today = date.today()
    start = today - timedelta(days=period_days)

    with Session(engine) as session:
        txs = session.exec(
            select(Transaction)
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(start))
            .order_by(Transaction.date)
        ).all()

    if not txs:
        return "Sin transacciones en el período para analizar."

    # Group by merchant or description (normalize to lowercase)
    groups: dict[str, list[Transaction]] = defaultdict(list)
    for tx in txs:
        key = (tx.merchant or tx.description).lower().strip()
        groups[key].append(tx)

    recurring = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        amounts = [t.amount for t in items]
        avg_amount = sum(amounts) / len(amounts)
        # Check amount stability: std dev < 20% of mean
        variance = sum((a - avg_amount) ** 2 for a in amounts) / len(amounts)
        std_dev = variance ** 0.5
        if std_dev / avg_amount > 0.20:
            continue  # amounts too variable — not a subscription

        dates = sorted(t.date for t in items)
        if len(dates) >= 2:
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            avg_gap = sum(gaps) / len(gaps)
            if avg_gap <= 10:
                freq = "semanal"
            elif avg_gap <= 20:
                freq = "quincenal"
            elif avg_gap <= 45:
                freq = "mensual"
            elif avg_gap <= 100:
                freq = "bimestral/trimestral"
            else:
                continue  # not recurring enough
        else:
            continue

        name = (items[0].merchant or items[0].description)[:30]
        recurring.append((name, avg_amount, freq, len(items), items[0].category))

    if not recurring:
        return f"No se detectaron pagos recurrentes en los últimos {period_days} días."

    recurring.sort(key=lambda x: -x[1])
    total_monthly = sum(
        amt if freq in ("mensual",) else amt * 2 if freq == "quincenal" else amt / 3
        for _, amt, freq, _, _ in recurring
    )

    lines = [f"🔄 Suscripciones y pagos recurrentes ({period_days} días):\n"]
    for name, amt, freq, count, cat in recurring:
        lines.append(f"  • {name} — ${amt:,.0f} ({freq}, {count} pagos, {cat})")

    lines.append(f"\nCosto mensual estimado: ${total_monthly:,.0f}")
    lines.append("Tip: Revisa si todas siguen siendo útiles — las duplicadas se pueden cancelar.")
    return "\n".join(lines)
