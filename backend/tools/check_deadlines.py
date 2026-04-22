from datetime import date

from langchain_core.tools import tool

# DIAN deadlines for declaración de renta personas naturales 2024 (last two NIT digits)
# Resolución DIAN 000094 de 2024
RENTA_2024_DEADLINES: dict[str, str] = {
    "01": "2025-08-12", "02": "2025-08-13", "03": "2025-08-14",
    "04": "2025-08-15", "05": "2025-08-18", "06": "2025-08-19",
    "07": "2025-08-20", "08": "2025-08-21", "09": "2025-08-22",
    "10": "2025-08-25", "11": "2025-08-26", "12": "2025-08-27",
    "13": "2025-08-28", "14": "2025-08-29", "15": "2025-09-01",
    "16": "2025-09-02", "17": "2025-09-03", "18": "2025-09-04",
    "19": "2025-09-05", "20": "2025-09-08", "21": "2025-09-09",
    "22": "2025-09-10", "23": "2025-09-11", "24": "2025-09-12",
    "25": "2025-09-15", "26": "2025-09-16", "27": "2025-09-17",
    "28": "2025-09-18", "29": "2025-09-19", "00": "2025-09-22",
}


@tool
def check_deadlines(nit_suffix: str = "") -> str:
    """Consulta las fechas límite de la DIAN para declaración de renta en Colombia.

    Args:
        nit_suffix: Últimos dos dígitos de tu NIT/cédula para ver tu fecha específica.
                    Deja vacío para ver el calendario completo.
    """
    today = date.today()

    if nit_suffix:
        suffix = nit_suffix.zfill(2)[-2:]
        deadline_str = RENTA_2024_DEADLINES.get(suffix)
        if not deadline_str:
            return f"No encontré fecha para el sufijo '{suffix}'. Verifica los últimos 2 dígitos de tu NIT."
        deadline = date.fromisoformat(deadline_str)
        days_left = (deadline - today).days
        status = (
            f"⏰ Quedan {days_left} días"
            if days_left > 0
            else ("🔴 VENCIDA" if days_left < 0 else "⚡ ¡Vence HOY!")
        )
        return (
            f"📅 Renta 2024 — NIT terminado en {suffix}:\n"
            f"  Fecha límite: {deadline.strftime('%d de %B de %Y')} {status}\n"
            f"\n💡 Presenta en dian.gov.co → Servicios en línea → Diligenciar y presentar declaraciones"
        )

    # Full calendar summary
    upcoming = [
        (suffix, date.fromisoformat(d))
        for suffix, d in RENTA_2024_DEADLINES.items()
        if date.fromisoformat(d) >= today
    ]
    upcoming.sort(key=lambda x: x[1])

    lines = ["📅 Calendario Renta 2024 — fechas pendientes:", ""]
    for suffix, d in upcoming[:10]:
        days_left = (d - today).days
        lines.append(f"  NIT …{suffix}: {d.strftime('%d %b %Y')} ({days_left}d)")
    if len(upcoming) > 10:
        lines.append(f"  … y {len(upcoming) - 10} fechas más hasta {upcoming[-1][1].strftime('%d %b')}")
    if not upcoming:
        lines = ["✅ Todas las fechas de renta 2024 ya vencieron."]

    lines.append(
        "\n💡 Más info en dian.gov.co"
    )
    return "\n".join(lines)
