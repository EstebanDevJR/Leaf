from datetime import datetime

from langchain_core.tools import tool
from sqlmodel import Session, select

from backend.db.database import engine
from backend.models.budget import Budget


@tool
def set_budget(category: str, monthly_limit: float) -> str:
    """Configura o actualiza el presupuesto mensual para una categoría de gastos.

    Args:
        category: Categoría del presupuesto (comida, transporte, vivienda,
                  salud, entretenimiento, ropa, servicios, otro).
        monthly_limit: Límite mensual en pesos colombianos (COP).
    """
    with Session(engine) as session:
        existing = session.exec(
            select(Budget).where(Budget.category == category)
        ).first()
        if existing:
            existing.monthly_limit = monthly_limit
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            return f"Presupuesto actualizado ✓ — {category}: ${monthly_limit:,.0f}/mes"
        budget = Budget(category=category, monthly_limit=monthly_limit)
        session.add(budget)
        session.commit()
        return f"Presupuesto configurado ✓ — {category}: ${monthly_limit:,.0f}/mes"
