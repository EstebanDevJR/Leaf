"""Tool: calculadora de sueldo neto y distribución de ahorro real."""

from langchain_core.tools import tool


@tool
def calculate_take_home_pay(sueldo_bruto: float) -> str:
    """Calcula cuánto te queda realmente de tu sueldo después de todos los descuentos.

    Incluye retención en la fuente (tabla DIAN 2026), seguridad social (salud + pensión)
    y fondo de solidaridad. Devuelve distribución recomendada 50/30/20 y proyección de ahorro.

    Args:
        sueldo_bruto: Ingreso mensual bruto en COP.
    """
    from backend.services.tax_calculator import calcular_take_home

    r = calcular_take_home(sueldo_bruto)
    d = r["descuentos"]
    dist = r["distribucion"]
    proy = r["proyecciones"]

    lines = [
        f"💼 Desglose salarial — ${r['sueldo_bruto']:,.0f} bruto\n",
        "Descuentos:",
        f"  Salud (4%):              ${d['salud']:,.0f}",
        f"  Pensión (4%):            ${d['pension']:,.0f}",
    ]
    if d["solidaridad"]:
        lines.append(f"  Fondo solidaridad:       ${d['solidaridad']:,.0f}")
    if d["retencion_fuente"]:
        lines.append(f"  Retención en la fuente:  ${d['retencion_fuente']:,.0f}")
    lines.append(f"  Total descuentos ({r['pct_descuento']}%): ${d['total']:,.0f}")
    lines.append(f"\n💵 Sueldo neto real:  ${r['sueldo_neto']:,.0f}\n")

    lines.append("Distribución recomendada (50/30/20):")
    lines.append(f"  🏠 Necesidades (50%):   ${dist['necesidades_50pct']:,.0f}  — arriendo, comida, transporte")
    lines.append(f"  🎉 Gustos (30%):        ${dist['gustos_30pct']:,.0f}  — salidas, streaming, hobbies")
    lines.append(f"  💰 Ahorro (20%):        ${dist['ahorro_20pct']:,.0f}/mes\n")

    lines.append("Proyección ahorro:")
    lines.append(f"  En 1 año:              ${proy['ahorro_anual']:,.0f}")
    lines.append(f"  En CDT al 11.5% EA:   +${proy['cdt_rendimiento_1a']:,.0f} de rendimiento")
    lines.append(f"  Total con CDT:         ${proy['total_con_cdt']:,.0f}\n")
    lines.append("¿Quieres que te arme un plan de ahorro personalizado o te muestre las mejores tasas CDT?")

    return "\n".join(lines)
