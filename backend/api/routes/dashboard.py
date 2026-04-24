"""Dashboard API — KPIs, cashflow histórico, fondo de emergencia, inversiones y simulador what-if."""

from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlmodel import Session, func, select

from backend.db.database import get_session
from backend.models.transaction import Transaction, TransactionType

router = APIRouter()


def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)
    return start, end


@router.get("/summary")
def get_summary(session: Session = Depends(get_session)) -> dict[str, Any]:
    """KPIs principales: balance, ingresos, gastos y deltas vs mes anterior."""
    now = datetime.utcnow()
    start_cur, _ = _month_bounds(now.year, now.month)

    prev = now.replace(day=1) - timedelta(days=1)
    start_prev, _ = _month_bounds(prev.year, prev.month)

    def _month_totals(start: datetime, end: datetime) -> tuple[float, float]:
        txs = list(session.exec(
            select(Transaction)
            .where(Transaction.date >= start)
            .where(Transaction.date < end)
        ).all())
        inc = sum(t.amount for t in txs if t.type == TransactionType.income)
        exp = sum(t.amount for t in txs if t.type == TransactionType.expense)
        return inc, exp

    cur_inc, cur_exp = _month_totals(start_cur, datetime(9999, 12, 31))
    prev_inc, prev_exp = _month_totals(start_prev, start_cur)

    total_income = session.exec(
        select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.income)
    ).one() or 0
    total_expenses = session.exec(
        select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.expense)
    ).one() or 0

    def _delta(cur: float, prev: float) -> float:
        return round((cur - prev) / prev * 100, 1) if prev > 0 else 0.0

    return {
        "balance": total_income - total_expenses,
        "month_income": cur_inc,
        "month_expenses": cur_exp,
        "month_savings": max(0.0, cur_inc - cur_exp),
        "savings_rate": round((cur_inc - cur_exp) / cur_inc * 100, 1) if cur_inc > 0 else 0.0,
        "income_delta_pct": _delta(cur_inc, prev_inc),
        "expenses_delta_pct": _delta(cur_exp, prev_exp),
        "transaction_count": session.exec(
            select(func.count(Transaction.id))
            .where(Transaction.date >= start_cur)
        ).one() or 0,
    }


@router.get("/cashflow")
def get_cashflow(
    months: int = 12,
    session: Session = Depends(get_session),
) -> list[dict[str, Any]]:
    """Cashflow histórico mensual (últimos N meses)."""
    now = datetime.utcnow()
    result: list[dict[str, Any]] = []

    for i in range(months - 1, -1, -1):
        # Compute year/month going back i months
        total_months = now.month - 1 - i
        year = now.year + total_months // 12
        month = total_months % 12 + 1
        if month <= 0:
            month += 12
            year -= 1

        start, end = _month_bounds(year, month)
        txs = list(session.exec(
            select(Transaction)
            .where(Transaction.date >= start)
            .where(Transaction.date < end)
        ).all())

        inc = sum(t.amount for t in txs if t.type == TransactionType.income)
        exp = sum(t.amount for t in txs if t.type == TransactionType.expense)

        MONTHS_ES = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        result.append({
            "label": MONTHS_ES[month - 1],
            "month": f"{year}-{month:02d}",
            "income": inc,
            "expenses": exp,
        })

    return result


@router.get("/expenses-breakdown")
def get_expenses_breakdown(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Distribución de gastos por categoría del mes actual."""
    now = datetime.utcnow()
    start, _ = _month_bounds(now.year, now.month)

    txs = list(session.exec(
        select(Transaction)
        .where(Transaction.date >= start)
        .where(Transaction.type == TransactionType.expense)
    ).all())

    by_cat: dict[str, float] = {}
    for t in txs:
        by_cat[t.category] = by_cat.get(t.category, 0) + t.amount

    total = sum(by_cat.values())
    return {
        "total": total,
        "by_category": by_cat,
        "percentages": {k: round(v / total * 100, 1) for k, v in by_cat.items()} if total else {},
    }


@router.get("/emergency-fund")
def get_emergency_fund(session: Session = Depends(get_session)) -> dict[str, Any]:
    """Estado estructurado del fondo de emergencia."""
    today = date.today()
    three_months_ago = today - timedelta(days=90)
    month_ago = today - timedelta(days=30)

    total_income = session.exec(
        select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.income)
    ).one() or 0
    total_expenses = session.exec(
        select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.expense)
    ).one() or 0
    recent_exp = session.exec(
        select(func.sum(Transaction.amount))
        .where(Transaction.type == TransactionType.expense)
        .where(Transaction.date >= str(three_months_ago))
    ).one() or 0
    inc_30 = session.exec(
        select(func.sum(Transaction.amount))
        .where(Transaction.type == TransactionType.income)
        .where(Transaction.date >= str(month_ago))
    ).one() or 0
    exp_30 = session.exec(
        select(func.sum(Transaction.amount))
        .where(Transaction.type == TransactionType.expense)
        .where(Transaction.date >= str(month_ago))
    ).one() or 0

    balance = total_income - total_expenses
    avg_monthly = recent_exp / 3 if recent_exp > 0 else 0
    coverage_months = balance / avg_monthly if avg_monthly > 0 else 0

    target_min = avg_monthly * 3
    target_recommended = avg_monthly * 5
    target_optimal = avg_monthly * 6

    monthly_savings = max(0.0, inc_30 - exp_30)
    gap = max(0.0, target_recommended - balance)
    months_to_goal = round(gap / monthly_savings, 1) if monthly_savings > 0 and gap > 0 else None

    if coverage_months >= 5:
        status = "complete"
    elif coverage_months >= 3:
        status = "warning"
    else:
        status = "critical"

    return {
        "balance": balance,
        "avg_monthly_expenses": avg_monthly,
        "coverage_months": round(coverage_months, 1),
        "target_min": target_min,
        "target_recommended": target_recommended,
        "target_optimal": target_optimal,
        "coverage_pct": round(min(100.0, balance / target_recommended * 100) if target_recommended > 0 else 0.0, 1),
        "gap": gap,
        "monthly_savings": monthly_savings,
        "months_to_goal": months_to_goal,
        "status": status,
    }


@router.get("/investments")
def get_investments() -> dict[str, Any]:
    """Tasas CDT actualizadas de bancos colombianos."""
    from backend.tools.cdt_live_rates import _get_rates
    rates, is_live, source_date = _get_rates()

    banks = []
    for bank, terms in rates.items():
        best_term = max(terms, key=lambda t: terms[t])
        banks.append({
            "bank": bank,
            "rates": terms,
            "best_rate": terms[best_term],
            "best_term": best_term,
        })

    banks.sort(key=lambda b: -b["best_rate"])

    return {
        "is_live": is_live,
        "source_date": source_date,
        "banks": banks,
        "inflation_rate": 5.5,
        "banrep_rate": 9.75,
    }


@router.post("/whatif")
def simulate_whatif(
    data: dict[str, Any],
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Simula escenarios What-If y devuelve proyecciones JSON."""
    today = date.today()
    three_months_ago = today - timedelta(days=90)

    base_income = (session.exec(
        select(func.sum(Transaction.amount))
        .where(Transaction.type == TransactionType.income)
        .where(Transaction.date >= str(three_months_ago))
    ).one() or 0) / 3

    base_expenses = (session.exec(
        select(func.sum(Transaction.amount))
        .where(Transaction.type == TransactionType.expense)
        .where(Transaction.date >= str(three_months_ago))
    ).one() or 0) / 3

    base_savings = base_income - base_expenses
    scenario: str = data.get("scenario", "ahorro_mas")
    change_pct: float = float(data.get("change_pct", 10))
    change_amount: float = float(data.get("change_amount", 0))

    if scenario == "ahorro_mas":
        extra = change_amount if change_amount else base_savings * (change_pct / 100)
        new_savings = base_savings + extra
        monthly_diff = extra
        label = f"Si ahorras {change_pct:.0f}% más"
    elif scenario == "gasto_menos":
        reduccion = change_amount if change_amount else base_expenses * (change_pct / 100)
        new_savings = base_income - (base_expenses - reduccion)
        monthly_diff = reduccion
        label = f"Si reduces gastos {change_pct:.0f}%"
    elif scenario == "ingreso_mas":
        aumento = change_amount if change_amount else base_income * (change_pct / 100)
        new_savings = (base_income + aumento) - base_expenses
        monthly_diff = aumento
        label = f"Si ganas {change_pct:.0f}% más"
    elif scenario == "categoria_cero":
        saved = change_amount if change_amount else base_expenses * 0.15
        new_savings = base_savings + saved
        monthly_diff = saved
        label = "Si eliminas una categoría de gasto"
    else:
        return {"error": f"Escenario '{scenario}' no reconocido"}

    projections: dict[str, Any] = {}
    for m in [1, 3, 6, 12, 24, 60]:
        projections[str(m)] = {
            "extra_savings": round(monthly_diff * m),
            "total_savings": round(new_savings * m),
            "vs_current": round(base_savings * m),
        }

    return {
        "scenario": scenario,
        "label": label,
        "base_income": base_income,
        "base_expenses": base_expenses,
        "base_savings": base_savings,
        "new_savings": new_savings,
        "monthly_diff": monthly_diff,
        "projections": projections,
    }
