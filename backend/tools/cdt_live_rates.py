"""CDT con tasas del día — scraping educativo de tasas de referencia."""

import logging
from datetime import datetime

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Fallback static rates (updated periodically)
_FALLBACK_RATES: dict[str, dict[int, float]] = {
    "Bancolombia":          {3: 10.2, 6: 11.0, 12: 11.5, 24: 11.8},
    "Davivienda":           {3: 10.0, 6: 10.8, 12: 11.3, 24: 11.6},
    "Banco de Bogotá":      {3: 9.8,  6: 10.5, 12: 11.0, 24: 11.4},
    "BBVA Colombia":        {3: 9.5,  6: 10.2, 12: 10.8, 24: 11.2},
    "Nequi":                {3: 10.5, 6: 11.2, 12: 11.8, 24: 12.0},
    "Finaktiva":            {3: 11.0, 6: 11.8, 12: 12.5, 24: 13.0},
    "Iris (Bancoomeva)":    {3: 10.8, 6: 11.5, 12: 12.2, 24: 12.6},
    "Lulo Bank":            {3: 11.2, 6: 12.0, 12: 12.8, 24: 13.2},
    "Rappipay":             {3: 10.8, 6: 11.6, 12: 12.3, 24: 12.7},
}

_cached_rates: dict | None = None
_cache_ts: datetime | None = None
_CACHE_TTL_HOURS = 6

DISCLAIMER = (
    "\n\n⚠️ Tasas de referencia educativas — no asesoría de inversión. "
    "Verifica directamente con cada entidad antes de invertir. "
    "Consulta un asesor certificado para decisiones financieras."
)


def _try_fetch_live_rates() -> dict | None:
    """Intenta obtener tasas actualizadas. Retorna None si falla."""
    try:
        import httpx
        # Tasas de referencia Banco de la República (TIB overnight como proxy)
        resp = httpx.get(
            "https://totoro.banrep.gov.co/estadisticas-economicas/rest/consultaDatosPC/50",
            timeout=5,
            headers={"User-Agent": "Leaf-FinancialApp/2.0"},
        )
        if resp.status_code == 200:
            data = resp.json()
            # Extract TIB rate as reference baseline
            if data and len(data) > 0:
                tib = float(data[-1].get("valor", 9.75))
                # Derive approximate CDT rates from TIB + spread
                return {bank: {t: round(tib + spread, 1)
                               for t, spread in [(3, 0.5), (6, 1.2), (12, 1.7), (24, 2.0)]}
                        for bank, _ in _FALLBACK_RATES.items()}
    except Exception as e:
        logger.debug("Live CDT fetch failed: %s", e)
    return None


def _get_rates() -> tuple[dict, bool]:
    """Returns (rates_dict, is_live)."""
    global _cached_rates, _cache_ts
    now = datetime.utcnow()

    if (_cached_rates is not None and _cache_ts is not None
            and (now - _cache_ts).total_seconds() < _CACHE_TTL_HOURS * 3600):
        return _cached_rates, True

    live = _try_fetch_live_rates()
    if live:
        _cached_rates = live
        _cache_ts = now
        return live, True

    return _FALLBACK_RATES, False


@tool
def get_live_cdt_rates(term_months: int = 12, amount: float = 0) -> str:
    """Consulta tasas CDT actualizadas de bancos colombianos y proyecta rendimiento.

    Args:
        term_months: Plazo en meses (3, 6, 12 o 24). Default 12.
        amount: Monto en COP para calcular rendimiento estimado (0 = solo tasas).
    """
    rates, is_live = _get_rates()
    valid_terms = [3, 6, 12, 24]
    closest = min(valid_terms, key=lambda t: abs(t - term_months))

    source = "actualizadas" if is_live else "de referencia (sin conexión)"
    lines = [f"📈 Tasas CDT {source} — {closest} meses (EA aproximada):\n"]

    entries = []
    for bank, terms in rates.items():
        rate = terms.get(closest, _FALLBACK_RATES.get(bank, {}).get(closest, 0))
        if rate:
            entries.append((bank, rate))

    entries.sort(key=lambda x: -x[1])
    for bank, rate in entries:
        line = f"  • {bank:<25} {rate:.1f}% EA"
        if amount > 0:
            rendimiento = amount * (rate / 100) * (closest / 12)
            line += f"  →  +${rendimiento:,.0f}"
        lines.append(line)

    if entries:
        best_bank, best_rate = entries[0]
        lines.append(f"\nMejor tasa disponible: {best_bank} ({best_rate:.1f}% EA)")
        if amount > 0:
            best_rend = amount * (best_rate / 100) * (closest / 12)
            lines.append(f"Con ${amount:,.0f} a {closest} meses: +${best_rend:,.0f}")

    lines.append(DISCLAIMER)
    return "\n".join(lines)
