"""Subscriptions REST endpoints — detecta suscripciones recurrentes en transacciones."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from backend.db.database import get_session
from backend.models.transaction import Transaction, TransactionType

router = APIRouter()


def _detect_subscriptions(transactions: list[Transaction], days: int = 90) -> list[dict]:
    """Agrupa transacciones por merchant/descripción y detecta patrones recurrentes."""
    cutoff = date.today() - timedelta(days=days)
    recent = [t for t in transactions if t.type == TransactionType.expense and t.date >= str(cutoff)]

    # Group by normalized merchant/description key
    groups: dict[str, list[Transaction]] = {}
    for t in recent:
        key = (t.merchant or t.description or "").lower().strip()[:40]
        if not key:
            continue
        groups.setdefault(key, []).append(t)

    subscriptions: list[dict] = []
    for key, txs in groups.items():
        if len(txs) < 2:
            continue
        amounts = [t.amount for t in txs]
        mean_amount = sum(amounts) / len(amounts)
        # Check stability: std < 20% of mean
        std = (sum((a - mean_amount) ** 2 for a in amounts) / len(amounts)) ** 0.5
        if mean_amount > 0 and std / mean_amount > 0.20:
            continue

        # Determine frequency from average gap
        dates_sorted = sorted(t.date for t in txs)
        if len(dates_sorted) < 2:
            continue
        from datetime import datetime
        date_objs = [datetime.fromisoformat(d).date() if "T" in d else date.fromisoformat(d) for d in dates_sorted]
        gaps = [(date_objs[i+1] - date_objs[i]).days for i in range(len(date_objs) - 1)]
        avg_gap = sum(gaps) / len(gaps)

        if avg_gap <= 10:
            frequency = "semanal"
            monthly_cost = mean_amount * 4.3
        elif avg_gap <= 20:
            frequency = "quincenal"
            monthly_cost = mean_amount * 2.0
        elif avg_gap <= 45:
            frequency = "mensual"
            monthly_cost = mean_amount
        elif avg_gap <= 100:
            frequency = "trimestral"
            monthly_cost = mean_amount / 3
        else:
            continue

        last_date = dates_sorted[-1]
        days_since = (date.today() - date_objs[-1]).days

        # Heuristic: potentially unused if no payment in last 45 days and > 3 months active
        potentially_unused = days_since > 45 and len(txs) >= 3

        subscriptions.append({
            "name": (txs[0].merchant or txs[0].description or key).title(),
            "category": txs[0].category,
            "amount_per_payment": round(mean_amount),
            "monthly_cost": round(monthly_cost),
            "frequency": frequency,
            "occurrences": len(txs),
            "last_payment": last_date,
            "days_since_last": days_since,
            "potentially_unused": potentially_unused,
        })

    subscriptions.sort(key=lambda s: -s["monthly_cost"])
    return subscriptions


@router.get("/")
def list_subscriptions(
    days: int = 90,
    session: Session = Depends(get_session),
) -> dict:
    """Detecta suscripciones recurrentes de los últimos N días."""
    transactions = list(session.exec(select(Transaction)).all())
    subs = _detect_subscriptions(transactions, days)

    total_monthly = sum(s["monthly_cost"] for s in subs)
    unused = [s for s in subs if s["potentially_unused"]]
    savings_potential = sum(s["monthly_cost"] for s in unused)

    return {
        "subscriptions": subs,
        "total_monthly": round(total_monthly),
        "total_annual": round(total_monthly * 12),
        "potentially_unused": unused,
        "savings_potential_monthly": round(savings_potential),
        "savings_potential_annual": round(savings_potential * 12),
        "count": len(subs),
    }
