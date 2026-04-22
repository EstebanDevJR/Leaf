from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def detect_anomaly(category: str = "all", threshold_pct: float = 50.0) -> str:
    """Detecta anomalías comparando el gasto de los últimos 30 días contra el promedio histórico de 3 meses.

    Args:
        category: Categoría a analizar o "all" para todas.
        threshold_pct: Porcentaje sobre el promedio que activa la alerta (default 50%).
    """
    today = date.today()
    current_start = today - timedelta(days=30)
    hist_start = today - timedelta(days=120)  # 90 días histórico previo a los últimos 30

    with Session(engine) as session:
        def _sum(start: date, end: date, cat: str | None) -> dict[str, float]:
            q = (
                select(Transaction.category, func.sum(Transaction.amount).label("t"))
                .where(Transaction.type == TransactionType.expense)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
                .group_by(Transaction.category)
            )
            if cat and cat != "all":
                q = q.where(Transaction.category == cat)
            return {row[0]: row[1] for row in session.exec(q).all()}

        current = _sum(current_start, today, None if category == "all" else category)
        historical = _sum(hist_start, current_start, None if category == "all" else category)

    if not current:
        return "Sin gastos en los últimos 30 días para analizar."

    anomalies = []
    normals = []

    for cat, total in current.items():
        hist_total = historical.get(cat, 0)
        # Historical covers 90 days → monthly average
        hist_avg = hist_total / 3 if hist_total > 0 else None

        if hist_avg is None:
            normals.append(f"  {cat}: ${total:,.0f} (sin historial previo)")
            continue

        delta_pct = (total - hist_avg) / hist_avg * 100
        if delta_pct > threshold_pct:
            anomalies.append(
                f"  🚨 {cat}: ${total:,.0f} "
                f"(+{delta_pct:.0f}% sobre promedio mensual ${hist_avg:,.0f})"
            )
        else:
            normals.append(
                f"  ✅ {cat}: ${total:,.0f} "
                f"(promedio ${hist_avg:,.0f}, {delta_pct:+.0f}%)"
            )

    lines = ["🔍 Detección de anomalías — últimos 30 días:\n"]
    if anomalies:
        lines.append("Anomalías detectadas:")
        lines.extend(anomalies)
    else:
        lines.append("No se detectaron anomalías de gasto.")
    if normals:
        lines.append("\nComportamiento normal:")
        lines.extend(normals)

    return "\n".join(lines)
