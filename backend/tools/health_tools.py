"""Tool: informe de salud financiera mensual con score 0-100."""

from langchain_core.tools import tool


@tool
def generate_financial_health_report() -> str:
    """Genera un informe de salud financiera con score 0-100, fortalezas, áreas de mejora
    y comparativa con el mes anterior. Úsalo cuando el usuario quiera saber cómo está financieramente.
    """
    from backend.services.health_calculator import compute_health_score

    r = compute_health_score()
    lines = [
        f"🌿 Informe de Salud Financiera — {r['month_label']}\n",
        f"Score: {r['score']}/100\n",
    ]

    if r["strengths"]:
        lines.append("Fortalezas:")
        for s in r["strengths"]:
            lines.append(f"  ✅ {s}")

    if r["improvements"]:
        lines.append("\nÁreas de mejora:")
        for imp in r["improvements"]:
            lines.append(f"  ⚠️  {imp}")

    lines.append(f"\nComparativa: {r['benchmark']}")
    lines.append(f"\nMeta del próximo mes: {r['next_month_goal']}")
    lines.append("\n¿Quieres que te ayude a mejorar alguna de las áreas débiles?")

    return "\n".join(lines)
