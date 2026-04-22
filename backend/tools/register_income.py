from langchain_core.tools import tool
from sqlmodel import Session

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType


@tool
def register_income(
    amount: float,
    category: str,
    description: str,
    source: str = None,
    notes: str = None,
) -> str:
    """Registra un ingreso en la base de datos.

    Args:
        amount: Monto del ingreso en pesos colombianos (COP). Siempre positivo.
        category: Categoría del ingreso. Opciones: salario, freelance, ventas,
                  inversiones, otro.
        description: Descripción breve del ingreso.
        source: Fuente o pagador del ingreso (opcional).
        notes: Notas adicionales (opcional).
    """
    tx = Transaction(
        amount=amount,
        description=description,
        category=category,
        type=TransactionType.income,
        merchant=source,
        notes=notes,
    )
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        session.refresh(tx)

    return f"Ingreso registrado ✓ — ${amount:,.0f} en {category} (ID: {tx.id})"
