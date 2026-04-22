from datetime import date

from langchain_core.tools import tool
from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.transaction import Transaction, TransactionType
from backend.tools.get_uvt import get_uvt


@tool
def check_obligacion(patrimonio: float = 0, nit_sufijo: str = "") -> str:
    """Determina si el usuario está obligado a declarar renta según la DIAN,
    considerando ingresos registrados en Leaf y el patrimonio informado.

    Args:
        patrimonio: Valor estimado del patrimonio bruto en COP
                    (bienes, cuentas, inversiones). Usa 0 si no aplica.
        nit_sufijo: Último dígito de la cédula/NIT para calcular fecha límite.
    """
    year = date.today().year
    uvt = get_uvt(year)
    start = date(year, 1, 1)
    end = date(year + 1, 1, 1)

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
                .where(Transaction.date >= str(start))
                .where(Transaction.date < str(end))
            ).one()
            or 0
        )

    tope_ingresos = 1_400 * uvt
    tope_patrimonio = 4_500 * uvt

    by_income = total_income > tope_ingresos
    by_patrimonio = patrimonio > tope_patrimonio
    obligado = by_income or by_patrimonio

    # DIAN 2025 renta (declaración 2026) — por último dígito de NIT
    calendario_2025 = {
        "0": "2026-04-09", "1": "2026-04-14", "2": "2026-04-16",
        "3": "2026-04-21", "4": "2026-04-23", "5": "2026-04-28",
        "6": "2026-04-30", "7": "2026-05-06", "8": "2026-05-08",
        "9": "2026-05-13",
    }

    lines = [
        f"⚖️ Análisis de obligación tributaria {year}:\n",
        f"  Ingresos registrados: ${total_income:,.0f}",
        f"  Tope ingresos:        ${tope_ingresos:,.0f} (1.400 UVT)  {'✅ bajo' if not by_income else '⚠️ SUPERA'}",
    ]
    if patrimonio > 0:
        lines.append(
            f"  Patrimonio declarado: ${patrimonio:,.0f}",
        )
        lines.append(
            f"  Tope patrimonio:      ${tope_patrimonio:,.0f} (4.500 UVT)  {'✅ bajo' if not by_patrimonio else '⚠️ SUPERA'}"
        )

    lines.append("")
    if obligado:
        lines.append("🔴 RESULTADO: Estás obligado a declarar renta.")
        if by_income:
            lines.append(f"   Motivo: ingresos superan 1.400 UVT (${tope_ingresos:,.0f})")
        if by_patrimonio:
            lines.append(f"   Motivo: patrimonio supera 4.500 UVT (${tope_patrimonio:,.0f})")
    else:
        lines.append("✅ RESULTADO: No estás obligado a declarar renta este año.")
        faltante = tope_ingresos - total_income
        lines.append(f"   Te faltan ${faltante:,.0f} de ingresos para el tope.")

    if obligado and nit_sufijo:
        digito = nit_sufijo.strip()[-1]
        fecha = calendario_2025.get(digito)
        if fecha:
            d = date.fromisoformat(fecha)
            days_left = (d - date.today()).days
            lines.append(
                f"\n📅 Tu fecha límite (NIT …{digito}): "
                f"{d.strftime('%d de %B de %Y')} — {days_left} días"
            )

    lines.append("\n⚠️ Estimación orientativa. Consulta a un contador.")
    return "\n".join(lines)
