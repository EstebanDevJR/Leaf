from datetime import date

from langchain_core.tools import tool

# Actualizar este dict cada enero con el nuevo valor publicado por la DIAN
UVT_POR_ANIO: dict[int, int] = {
    2023: 42_412,
    2024: 47_065,
    2025: 49_799,  # ← actualizar aquí cada enero
}


def get_uvt(year: int | None = None) -> int:
    year = year or date.today().year
    return UVT_POR_ANIO.get(year, UVT_POR_ANIO[max(UVT_POR_ANIO)])


@tool
def get_uvt_vigente(year: int = 0) -> str:
    """Retorna el valor UVT vigente y los topes tributarios clave en COP.

    Args:
        year: Año a consultar. Usa 0 para el año en curso.
    """
    if year == 0:
        year = date.today().year
    uvt = get_uvt(year)

    thresholds = {
        "Obligación declarar (ingresos)":       1_400,
        "Obligación declarar (patrimonio)":     4_500,
        "Retención mínima honorarios":             87,
        "Renta exenta trabajo (25%, máx)":      2_880,
        "Deducción intereses vivienda (máx)":   1_200,
        "Retención mínima servicios":              27,
    }

    lines = [
        f"📏 UVT {year}: ${uvt:,} COP",
        "",
        "Topes tributarios:",
    ]
    for concepto, uvts in thresholds.items():
        cop = uvts * uvt
        lines.append(f"  {concepto}: {uvts:,} UVT = ${cop:,.0f}")

    lines.append(
        "\n💡 El valor UVT lo publica la DIAN cada enero mediante resolución."
    )
    return "\n".join(lines)
