"""CDT rates from Superfinanciera (SFC) via datos.gov.co — live data."""

import logging
from datetime import datetime, date

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# datos.gov.co SFC dataset: "Tasas de interés de captación y operaciones del mercado monetario"
_SFC_URL = "https://www.datos.gov.co/resource/axk9-g2nh.json"

# SFC entity name → friendly display name
_ENTITY_MAP: dict[str, str] = {
    "Bancolombia": "Bancolombia",
    "Banco Davivienda": "Davivienda",
    "Banco de Bogotá S.A.": "Banco de Bogotá",
    "BBVA Colombia": "BBVA Colombia",
    "Finandina Bic o Banco Finandina Bic o Finandina.": "Finandina",
    "Bancoomeva": "Bancoomeva",
    "IRIS CF.": "Iris CF",
    "NU COLOMBIA COMPAÑÍA DE FINANCIAMIENTO S.A.": "NU Colombia",
    "Banco Santander": "Banco Santander",
    "Banco de Occidente": "Banco de Occidente",
    "Banco GNB Sudameris": "GNB Sudameris",
    "Banco Pichincha S.A.": "Banco Pichincha",
    "Mibanco S.A.": "Mibanco",
    "Banco Popular": "Banco Popular",
    "Banco Caja Social S.A.": "Banco Caja Social",
    "AV Villas": "AV Villas",
    "Banco Serfinanza S.A.": "Banco Serfinanza",
    "Coltefinanciera": "Coltefinanciera",
    "Itaú; Banco Itaú.": "Banco Itaú",
    "BANCO CONTACTAR S.A.": "Banco Contactar",
    "Banco Falabella S.A.": "Banco Falabella",
    "KOA CF": "KOA CF",
    "Tuya": "Tuya",
    "Banco W S.A.": "Banco W",
    "Banco Credifinanciera S.A.": "Credifinanciera",
    "Bancamía S.A.": "Bancamía",
    "Banco Colpatria": "Banco Colpatria",
    "BANCO UNIÓN S.A. (en adelante el \"Banco\" o la \"Sociedad\")": "Banco Unión",
}

# subcuenta → CDT term in months (uca=1 CDT dataset)
# sub=70:  A 90 DIAS       → 3 months
# sub=110: A 180 DIAS      → 6 months
# sub=130: A 360 DIAS      → 12 months
# sub=140: >360 DIAS       → 24 months
_SUB_TO_TERM: dict[str, int] = {"70": 3, "110": 6, "130": 12, "140": 24}

# Static fallback (SFC data as of 2026-04-21, source: datos.gov.co)
_FALLBACK_RATES: dict[str, dict[int, float]] = {
    "Bancolombia":      {3: 9.6,  6: 10.3, 12: 12.6, 24: 10.6},
    "Davivienda":       {3: 9.3,  6: 9.4,  12: 10.5, 24: 11.4},
    "Banco de Bogotá":  {3: 10.7, 6: 10.8, 12: 13.4, 24: 13.5},
    "BBVA Colombia":    {3: 10.2, 6: 10.3, 12: 12.3, 24: 13.8},
    "Finandina":        {3: 11.7, 6: 11.4, 12: 12.0, 24: 12.5},
    "Bancoomeva":       {3: 10.2, 6: 10.1, 12: 13.3, 24: 14.0},
    "NU Colombia":      {3: 9.9,  6: 10.1, 12: 11.0, 24: 10.8},
    "Banco Santander":  {3: 11.0, 6: 11.9, 12: 13.0, 24: 13.3},
    "Banco de Occidente":{3: 11.6, 6: 11.9, 12: 13.2, 24: 12.7},
    "GNB Sudameris":    {3: 11.2, 6: 10.5, 12: 12.0, 24: 12.4},
    "Banco Pichincha":  {3: 9.9,  6: 11.1, 12: 13.0, 24: 13.0},
    "Mibanco":          {3: 11.2, 6: 12.0, 12: 12.5, 24: 12.4},
    "Banco Popular":    {3: 9.9,  6: 10.4, 12: 11.9, 24: 12.1},
    "Banco Caja Social":{3: 8.2,  6: 8.9,  12: 9.4,  24: 9.5},
    "Coltefinanciera":  {3: 10.6, 6: 11.4, 12: 11.7, 24: 13.6},
    "Banco Itaú":       {3: 10.2, 6: 10.5, 12: 12.2, 24: 12.2},
    "Banco Falabella":  {3: 11.0, 6: 11.0, 12: 12.2, 24: 10.9},
    "Banco Colpatria":  {3: 10.5, 6: 11.2, 12: 10.8, 24: 10.8},
}
_FALLBACK_DATE = "2026-04-21"

_cached_rates: dict | None = None
_cache_ts: datetime | None = None
_cache_date: str = _FALLBACK_DATE
_CACHE_TTL_HOURS = 6

DISCLAIMER = (
    "\n\n⚠️ Tasas reportadas a la Superfinanciera de Colombia (SFC). "
    "Varían según monto y condiciones. Verifica con cada entidad antes de invertir."
)


def _try_fetch_live_rates() -> tuple[dict, str] | None:
    """Fetch CDT rates from SFC via datos.gov.co. Returns (rates, date_str) or None."""
    try:
        import httpx
        with httpx.Client(timeout=8, headers={"User-Agent": "Leaf-FinancialApp/2.0"}) as client:
            resp = client.get(
                _SFC_URL,
                params={
                    "uca": "1",
                    "$where": "subcuenta IN('70','110','130','140') AND fechacorte > '2026-01-01T00:00:00.000'",
                    "$order": "fechacorte DESC",
                    "$limit": "500",
                    "$select": "nombreentidad,subcuenta,tasa,fechacorte",
                },
            )
            if resp.status_code != 200:
                return None

            rows = resp.json()
            if not rows:
                return None

            latest_date = max(r["fechacorte"][:10] for r in rows)

            rates: dict[str, dict[int, float]] = {}
            for row in rows:
                if row["fechacorte"][:10] != latest_date:
                    continue
                entity = row["nombreentidad"].strip('"').strip()
                display = _ENTITY_MAP.get(entity, entity)
                term = _SUB_TO_TERM.get(row["subcuenta"].strip())
                if term is None:
                    continue
                tasa = float(row["tasa"])
                if tasa <= 0:
                    continue
                if display not in rates:
                    rates[display] = {}
                if term not in rates[display] or tasa > rates[display][term]:
                    rates[display][term] = round(tasa, 2)

            # Only include banks with at least 2 terms
            rates = {k: v for k, v in rates.items() if len(v) >= 2}
            if not rates:
                return None
            return rates, latest_date
    except Exception as e:
        logger.debug("SFC CDT fetch failed: %s", e)
        return None


def _get_rates() -> tuple[dict, bool, str]:
    """Returns (rates_dict, is_live, source_date)."""
    global _cached_rates, _cache_ts, _cache_date
    now = datetime.utcnow()

    if (_cached_rates is not None and _cache_ts is not None
            and (now - _cache_ts).total_seconds() < _CACHE_TTL_HOURS * 3600):
        return _cached_rates, True, _cache_date

    result = _try_fetch_live_rates()
    if result is not None:
        live, date_str = result
        _cached_rates = live
        _cache_ts = now
        _cache_date = date_str
        return live, True, date_str

    return _FALLBACK_RATES, False, _FALLBACK_DATE


@tool
def get_live_cdt_rates(term_months: int = 12, amount: float = 0) -> str:
    """Consulta tasas CDT actualizadas de bancos colombianos reportadas a la SFC.

    Args:
        term_months: Plazo en meses (3, 6, 12 o 24). Default 12.
        amount: Monto en COP para calcular rendimiento estimado (0 = solo tasas).
    """
    rates, is_live, source_date = _get_rates()
    valid_terms = [3, 6, 12, 24]
    closest = min(valid_terms, key=lambda t: abs(t - term_months))

    source = f"SFC datos.gov.co ({source_date})" if is_live else f"referencia ({source_date})"
    lines = [f"📈 Tasas CDT — {closest} meses | Fuente: {source}\n"]

    entries = []
    for bank, terms in rates.items():
        rate = terms.get(closest)
        if rate:
            entries.append((bank, rate))

    entries.sort(key=lambda x: -x[1])
    for bank, rate in entries:
        line = f"  • {bank:<28} {rate:.2f}% EA"
        if amount > 0:
            rendimiento = amount * (rate / 100) * (closest / 12)
            line += f"  →  +${rendimiento:,.0f}"
        lines.append(line)

    if entries:
        best_bank, best_rate = entries[0]
        lines.append(f"\nMejor tasa disponible: {best_bank} ({best_rate:.2f}% EA)")
        if amount > 0:
            best_rend = amount * (best_rate / 100) * (closest / 12)
            lines.append(f"Con ${amount:,.0f} a {closest} meses: +${best_rend:,.0f}")

    lines.append(DISCLAIMER)
    return "\n".join(lines)
