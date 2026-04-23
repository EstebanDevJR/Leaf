"""Calculadora de score de salud financiera (0-100)."""

from datetime import date, datetime, timedelta

from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


def _get_period_totals(session: Session, start: date, end: date) -> tuple[float, float]:
    txs = list(session.exec(
        select(Transaction)
        .where(Transaction.date >= str(start))
        .where(Transaction.date < str(end))
    ).all())
    inc = sum(t.amount for t in txs if t.type == TransactionType.income)
    exp = sum(t.amount for t in txs if t.type == TransactionType.expense)
    return inc, exp


def _get_category_totals(session: Session, start: date, end: date) -> dict[str, float]:
    txs = list(session.exec(
        select(Transaction)
        .where(Transaction.date >= str(start))
        .where(Transaction.date < str(end))
        .where(Transaction.type == TransactionType.expense)
    ).all())
    by_cat: dict[str, float] = {}
    for t in txs:
        by_cat[t.category] = by_cat.get(t.category, 0) + t.amount
    return by_cat


def compute_health_score() -> dict:
    today = date.today()
    # Current month
    cur_start = today.replace(day=1)
    if cur_start.month == 12:
        cur_end = date(cur_start.year + 1, 1, 1)
    else:
        cur_end = date(cur_start.year, cur_start.month + 1, 1)

    # Previous month
    prev_end = cur_start
    prev_first = (cur_start - timedelta(days=1)).replace(day=1)

    # Last 3 months for emergency fund calc
    three_months_ago = today - timedelta(days=90)

    with Session(engine) as session:
        cur_inc, cur_exp = _get_period_totals(session, cur_start, cur_end)
        prev_inc, prev_exp = _get_period_totals(session, prev_first, prev_end)
        cur_cats = _get_category_totals(session, cur_start, cur_end)
        prev_cats = _get_category_totals(session, prev_first, prev_end)

        total_income_all = session.exec(
            select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.income)
        ).one() or 0
        total_exp_all = session.exec(
            select(func.sum(Transaction.amount)).where(Transaction.type == TransactionType.expense)
        ).one() or 0
        recent_exp = session.exec(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(three_months_ago))
        ).one() or 0

        # Savings goals
        try:
            from backend.models.savings_goal import SavingsGoal
            goals = list(session.exec(select(SavingsGoal)).all())
        except Exception:
            goals = []

        # Budgets
        try:
            from backend.models.budget import Budget
            budgets = list(session.exec(select(Budget)).all())
        except Exception:
            budgets = []

    balance = total_income_all - total_exp_all
    avg_monthly_exp = recent_exp / 3 if recent_exp > 0 else 0
    coverage_months = balance / avg_monthly_exp if avg_monthly_exp > 0 else 0

    # ── Scoring (0-100) ────────────────────────────────────────────────────
    score = 0
    strengths: list[str] = []
    improvements: list[str] = []

    # 1. Tasa de ahorro (max 30 pts)
    savings_rate = (cur_inc - cur_exp) / cur_inc if cur_inc > 0 else 0
    if savings_rate >= 0.20:
        score += 30
        strengths.append(f"Ahorraste {savings_rate:.0%} de tus ingresos (meta: 20%) ✅")
    elif savings_rate >= 0.10:
        score += 18
        strengths.append(f"Ahorraste {savings_rate:.0%} de tus ingresos (buen comienzo)")
    elif savings_rate > 0:
        score += 8
        improvements.append(f"Solo ahorraste {savings_rate:.0%} — intenta llegar al 20%")
    else:
        improvements.append("Gastos superan ingresos este mes — revisa tus categorías")

    # 2. Fondo de emergencia (max 25 pts)
    if coverage_months >= 5:
        score += 25
        strengths.append(f"Fondo de emergencia al {min(100, coverage_months/5*100):.0f}% ({coverage_months:.1f} meses) ✅")
    elif coverage_months >= 3:
        score += 15
        strengths.append(f"Fondo de emergencia parcial ({coverage_months:.1f} meses de {5} recomendados)")
    elif coverage_months >= 1:
        score += 7
        improvements.append(f"Fondo de emergencia bajo ({coverage_months:.1f} meses) — meta: 5 meses de gastos")
    else:
        improvements.append("Sin fondo de emergencia — prioridad urgente")

    # 3. Comparativa vs mes anterior (max 15 pts)
    if prev_exp > 0:
        exp_change = (cur_exp - prev_exp) / prev_exp
        if exp_change <= -0.05:
            score += 15
            strengths.append(f"Redujiste gastos {abs(exp_change):.0%} vs el mes pasado ✅")
        elif exp_change <= 0.05:
            score += 10
            strengths.append("Gastos estables vs el mes pasado")
        elif exp_change <= 0.20:
            score += 5
            improvements.append(f"Gastos subieron {exp_change:.0%} vs el mes pasado")
        else:
            improvements.append(f"Gastos subieron {exp_change:.0%} vs el mes pasado — revisa qué cambió")

    # 4. Metas de ahorro activas (max 15 pts)
    active_goals = [g for g in goals if not g.completed_at]
    if active_goals:
        score += 15
        strengths.append(f"Tienes {len(active_goals)} meta(s) de ahorro activa(s) ✅")
    else:
        improvements.append("Sin metas de ahorro — crea una para enfocar tu dinero")

    # 5. Control de presupuesto (max 10 pts)
    budget_violations = []
    for b in budgets:
        cat_spent = cur_cats.get(b.category, 0)
        if cat_spent > b.monthly_limit:
            budget_violations.append(b.category)
    if not budget_violations and budgets:
        score += 10
        strengths.append(f"Respetaste todos tus presupuestos este mes ✅")
    elif budget_violations:
        score += 3
        improvements.append(f"Excediste presupuesto en: {', '.join(budget_violations)}")
    elif not budgets:
        improvements.append("No tienes presupuestos configurados — te ayudan a controlar gastos")

    # 5. Categorías problemáticas (bonus/malus para improvements)
    FOOD_WARN_RATIO = 0.40  # si comida > 40% del gasto
    total_cat = sum(cur_cats.values())
    if total_cat > 0:
        for cat, amt in sorted(cur_cats.items(), key=lambda x: -x[1]):
            if cat == "comida" and amt / total_cat > FOOD_WARN_RATIO:
                improvements.append(f"Comida representa {amt/total_cat:.0%} del gasto — considera cocinar más en casa")
                break

    # Benchmark
    if score >= 80:
        benchmark = "Estás mejor que el 80% de colombianos con tu perfil financiero 🏆"
    elif score >= 60:
        benchmark = "Estás mejor que el 60% de colombianos con tu perfil financiero"
    elif score >= 40:
        benchmark = "Estás en el promedio de colombianos con tu perfil — hay espacio para mejorar"
    else:
        benchmark = "Tienes oportunidad de mejorar significativamente tu situación financiera"

    # Next month goal
    if score >= 80:
        next_goal = f"Mantener score sobre 80 e iniciar una inversión CDT si aún no lo has hecho"
    elif score < 50:
        next_goal = f"Construir fondo de emergencia (meta: 3 meses de gastos) y reducir gastos"
    else:
        next_goal = f"Llegar a {min(100, score + 10)}/100 — enfócate en: {improvements[0] if improvements else 'mantener el rumbo'}"

    month_label = today.strftime("%B %Y").capitalize()

    return {
        "month": today.strftime("%Y-%m"),
        "month_label": month_label,
        "score": min(100, score),
        "strengths": strengths,
        "improvements": improvements,
        "benchmark": benchmark,
        "next_month_goal": next_goal,
        "details": {
            "savings_rate": round(savings_rate * 100, 1),
            "coverage_months": round(coverage_months, 1),
            "active_goals": len(active_goals),
            "budget_violations": len(budget_violations),
            "month_income": cur_inc,
            "month_expenses": cur_exp,
        },
    }
