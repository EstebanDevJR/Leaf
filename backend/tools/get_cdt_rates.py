from langchain_core.tools import tool

# Reference CDT rates (approximate EA, updated periodically — verify with each bank)
CDT_RATES: dict[str, dict[int, float]] = {
    "Bancolombia":   {3: 10.2, 6: 11.0, 12: 11.5, 24: 11.8},
    "Davivienda":    {3: 10.0, 6: 10.8, 12: 11.3, 24: 11.6},
    "Banco de Bogotá": {3: 9.8, 6: 10.5, 12: 11.0, 24: 11.4},
    "BBVA Colombia": {3: 9.5, 6: 10.2, 12: 10.8, 24: 11.2},
    "Nequi / Bancolombia digital": {3: 10.5, 6: 11.2, 12: 11.8, 24: 12.0},
    "Finaktiva":     {3: 11.0, 6: 11.8, 12: 12.5, 24: 13.0},
    "Iris (Bancoomeva)": {3: 10.8, 6: 11.5, 12: 12.2, 24: 12.6},
}

DISCLAIMER = (
    "\n\n⚠️ Esta es información educativa, no asesoría de inversión. "
    "Las tasas son de referencia y cambian frecuentemente. "
    "Consulta directamente con el banco antes de invertir. "
    "Consulta un asesor certificado para decisiones financieras."
)


@tool
def get_cdt_rates(term_months: int = 12, amount: float = 0) -> str:
    """Consulta tasas CDT de referencia en bancos colombianos y proyecta rendimiento.

    Args:
        term_months: Plazo en meses (3, 6, 12 o 24). Default 12.
        amount: Monto a invertir en COP para calcular rendimiento estimado. 0 = solo tasas.
    """
    valid_terms = [3, 6, 12, 24]
    closest = min(valid_terms, key=lambda t: abs(t - term_months))

    lines = [f"📈 Tasas CDT de referencia — {closest} meses (EA aproximada):\n"]
    rates_for_term = []
    for bank, terms in CDT_RATES.items():
        rate = terms.get(closest)
        if rate:
            rates_for_term.append((bank, rate))
            line = f"  • {bank}: {rate:.1f}% EA"
            if amount > 0:
                rendimiento = amount * (rate / 100) * (closest / 12)
                line += f"  →  +${rendimiento:,.0f} en {closest} meses"
            lines.append(line)

    if rates_for_term:
        best_bank, best_rate = max(rates_for_term, key=lambda x: x[1])
        lines.append(f"\nMejor tasa: {best_bank} ({best_rate:.1f}% EA)")
        if amount > 0:
            best_rendimiento = amount * (best_rate / 100) * (closest / 12)
            lines.append(
                f"Con ${amount:,.0f} a {closest} meses ganarías ~${best_rendimiento:,.0f}"
            )

    lines.append(DISCLAIMER)
    return "\n".join(lines)
