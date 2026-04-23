"""Simulador de escenarios What-If financieros."""

from datetime import date, timedelta

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


def _get_monthly_base(session: Session) -> tuple[float, float]:
    """Returns (avg_monthly_income, avg_monthly_expenses) for last 3 months."""
    start = date.today() - timedelta(days=90)
    income = (
        session.exec(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.income)
            .where(Transaction.date >= str(start))
        ).one() or 0
    ) / 3
    expenses = (
        session.exec(
            select(func.sum(Transaction.amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.date >= str(start))
        ).one() or 0
    ) / 3
    return income, expenses


@tool
def whatif_simulator(
    scenario: str,
    change_pct: float = 0,
    change_amount: float = 0,
    months: int = 12,
) -> str:
    """Simula escenarios financieros 'What-If' y proyecta el impacto en tus finanzas.

    Escenarios disponibles:
    - 'ahorro_mas': ¿Qué pasa si ahorro X% más cada mes?
    - 'gasto_menos': ¿Qué pasa si reduzco gastos en X%?
    - 'ingreso_mas': ¿Qué pasa si gano X% más?
    - 'categoria_cero': ¿Qué pasa si elimino una categoría de gasto?

    Args:
        scenario: Nombre del escenario (ver opciones arriba).
        change_pct: Cambio porcentual (ej: 15 para 15% más).
        change_amount: Cambio en pesos COP (alternativo a change_pct).
        months: Horizonte de proyección en meses (default 12).
    """
    with Session(engine) as session:
        base_income, base_expenses = _get_monthly_base(session)

    if base_income == 0 and base_expenses == 0:
        return "Sin datos históricos suficientes para simular. Registra al menos 1 mes de transacciones."

    base_savings = base_income - base_expenses

    lines = [f"🔮 Simulación What-If: '{scenario}' | Horizonte: {months} meses\n"]
    lines.append(f"Base actual:")
    lines.append(f"  Ingresos/mes:  ${base_income:,.0f}")
    lines.append(f"  Gastos/mes:    ${base_expenses:,.0f}")
    lines.append(f"  Ahorro/mes:    ${base_savings:,.0f}")

    delta = change_amount if change_amount != 0 else 0

    if scenario == "ahorro_mas":
        extra = base_savings * (change_pct / 100) if change_pct else change_amount
        new_savings = base_savings + extra
        new_expenses = base_expenses - extra
        lines.append(f"\nEscenario: ahorras {change_pct:.0f}% más (+${extra:,.0f}/mes)")
        lines.append(f"  Nuevos gastos:    ${new_expenses:,.0f}/mes")
        lines.append(f"  Nuevo ahorro:     ${new_savings:,.0f}/mes")
        lines.append(f"  Ahorro en {months} meses: ${new_savings * months:,.0f}")
        lines.append(f"  vs. sin cambio:   ${base_savings * months:,.0f}")
        lines.append(f"  Diferencia:       +${(new_savings - base_savings) * months:,.0f}")

    elif scenario == "gasto_menos":
        reduccion = base_expenses * (change_pct / 100) if change_pct else change_amount
        new_expenses = base_expenses - reduccion
        new_savings = base_income - new_expenses
        lines.append(f"\nEscenario: reduces gastos {change_pct:.0f}% (-${reduccion:,.0f}/mes)")
        lines.append(f"  Nuevos gastos:    ${new_expenses:,.0f}/mes")
        lines.append(f"  Nuevo ahorro:     ${new_savings:,.0f}/mes")
        lines.append(f"  Ahorro en {months} meses: ${new_savings * months:,.0f}")
        lines.append(f"  vs. sin cambio:   ${base_savings * months:,.0f}")
        lines.append(f"  Diferencia:       +${(new_savings - base_savings) * months:,.0f}")

    elif scenario == "ingreso_mas":
        aumento = base_income * (change_pct / 100) if change_pct else change_amount
        new_income = base_income + aumento
        new_savings = new_income - base_expenses
        lines.append(f"\nEscenario: ingresas {change_pct:.0f}% más (+${aumento:,.0f}/mes)")
        lines.append(f"  Nuevos ingresos:  ${new_income:,.0f}/mes")
        lines.append(f"  Nuevo ahorro:     ${new_savings:,.0f}/mes")
        lines.append(f"  Ahorro en {months} meses: ${new_savings * months:,.0f}")
        lines.append(f"  vs. sin cambio:   ${base_savings * months:,.0f}")
        lines.append(f"  Diferencia:       +${(new_savings - base_savings) * months:,.0f}")

    elif scenario == "categoria_cero":
        saved_monthly = change_amount if change_amount else base_expenses * 0.15
        new_savings = base_savings + saved_monthly
        lines.append(f"\nEscenario: eliminas una categoría de gasto (${saved_monthly:,.0f}/mes)")
        lines.append(f"  Ahorro extra/mes: ${saved_monthly:,.0f}")
        lines.append(f"  Nuevo ahorro:     ${new_savings:,.0f}/mes")
        lines.append(f"  Ahorro en {months} meses: ${new_savings * months:,.0f}")
        lines.append(f"  Extra acumulado:  +${saved_monthly * months:,.0f}")

    else:
        return (
            f"Escenario '{scenario}' no reconocido.\n"
            "Opciones: ahorro_mas, gasto_menos, ingreso_mas, categoria_cero"
        )

    # Projection: balance accumulated over months
    if scenario in ("ahorro_mas", "gasto_menos"):
        monthly_diff = new_savings - base_savings
    elif scenario == "ingreso_mas":
        monthly_diff = new_savings - base_savings
    else:
        monthly_diff = change_amount if change_amount else base_expenses * 0.15

    lines.append(f"\n📈 Proyección acumulada (vs. sin cambio):")
    for m in (3, 6, 12, 24):
        if m <= months:
            lines.append(f"  {m:>2} meses: +${monthly_diff * m:,.0f}")

    return "\n".join(lines)
