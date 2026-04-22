from langchain_core.tools import tool

CONCEPTS: dict[str, str] = {
    "cdt": (
        "Un CDT (Certificado de Depósito a Término) es un producto de ahorro bancario donde depositas "
        "dinero por un plazo fijo (3, 6, 12 o 24 meses) y el banco te paga una tasa de interés acordada.\n\n"
        "Cómo funciona:\n"
        "  • Depositas un monto mínimo (usualmente $1.000.000 COP).\n"
        "  • El banco te garantiza una tasa EA (efectiva anual) fija.\n"
        "  • Al vencer el plazo, recibes el capital + intereses.\n"
        "  • No puedes retirar antes sin penalización.\n\n"
        "Ventajas: seguro (FOGAFÍN cubre hasta $50M), sin riesgo de mercado.\n"
        "Desventaja: ilíquido durante el plazo."
    ),
    "uvt": (
        "La UVT (Unidad de Valor Tributario) es la unidad de medida que usa la DIAN para expresar "
        "montos tributarios de forma que se actualicen con la inflación.\n\n"
        "Valores: 2023: $42.412 | 2024: $47.065 | 2025: $49.799 COP\n\n"
        "Se usa para calcular:\n"
        "  • Topes de obligación de declarar renta (1.400 UVT ~ $69.7M en 2025)\n"
        "  • Rangos del impuesto de renta\n"
        "  • Topes de deducción (salud, vivienda, etc.)"
    ),
    "gmf": (
        "El GMF (Gravamen a los Movimientos Financieros) o '4×1000' es un impuesto del 0.4% "
        "que se cobra sobre cada transacción bancaria en Colombia.\n\n"
        "Lo descuenta automáticamente tu banco en cada retiro o transferencia.\n\n"
        "Dato clave: el 50% de lo pagado es deducible en tu declaración de renta, "
        "pero solo si tienes cuenta de ahorros exenta designada."
    ),
    "retencion": (
        "La retención en la fuente es un anticipo del impuesto de renta que te descuentan "
        "cuando recibes pagos por servicios.\n\n"
        "Para independientes/freelancers:\n"
        "  • Honorarios: ~10-11%\n"
        "  • Servicios: ~4-6%\n"
        "  • Consultoría: ~10%\n\n"
        "No es un impuesto adicional — es un descuento anticipado que se cruza con tu "
        "declaración de renta al final del año."
    ),
    "renta": (
        "El impuesto de renta es un tributo anual sobre tus ingresos.\n\n"
        "Debes declarar si en 2025 tuviste:\n"
        "  • Ingresos brutos > 1.400 UVT (~$69.7M)\n"
        "  • Patrimonio bruto > 4.500 UVT (~$224M)\n"
        "  • Consumos con tarjeta > 1.400 UVT\n\n"
        "Tasas progresivas (2025): desde 0% hasta 39% según renta líquida gravable.\n"
        "Leaf puede estimarlo con 'calcula mi impuesto de renta'."
    ),
    "fiducia": (
        "Una fiducia (o fondo de inversión colectiva) es un vehículo donde varios inversionistas "
        "juntan capital y una fiduciaria lo gestiona invirtiendo en renta fija, acciones u otros activos.\n\n"
        "Tipos comunes en Colombia:\n"
        "  • Fiducia de renta fija: bajo riesgo, liquidez diaria, ~9-12% EA\n"
        "  • Fondo en acciones: mayor riesgo y potencial de ganancia\n\n"
        "Ventaja vs CDT: más liquidez. Desventaja: tasa variable."
    ),
    "fondo de emergencia": (
        "El fondo de emergencia es un colchón de ahorro líquido para cubrir imprevistos "
        "sin endeudarse.\n\n"
        "Regla general: entre 3 y 6 meses de tus gastos mensuales.\n\n"
        "Ejemplo: si gastas $2.000.000/mes, tu fondo debe ser entre $6M y $12M.\n\n"
        "Dónde guardarlo: cuenta de ahorros de alta rentabilidad o CDT a corto plazo — "
        "accesible pero separado de tu cuenta corriente."
    ),
    "presupuesto": (
        "Un presupuesto es un plan de cómo distribuirás tus ingresos entre gastos y ahorro.\n\n"
        "Método popular — regla 50/30/20:\n"
        "  • 50% necesidades (vivienda, comida, transporte)\n"
        "  • 30% deseos (entretenimiento, ropa, ocio)\n"
        "  • 20% ahorro/deuda\n\n"
        "En Leaf puedes configurar límites por categoría con 'establece presupuesto para comida'."
    ),
    "tasa ea": (
        "La tasa EA (Efectiva Anual) es la tasa de interés real que ganas o pagas en un año, "
        "incluyendo la capitalización.\n\n"
        "Ejemplo: un CDT al 11.5% EA sobre $10.000.000 genera $1.150.000 en 12 meses.\n\n"
        "No confundir con tasa nominal (MV, TV, SV) que no incluye el efecto del interés compuesto. "
        "Siempre compara productos financieros usando la tasa EA."
    ),
}


@tool
def explain_concept(concept: str) -> str:
    """Explica conceptos financieros en lenguaje simple con contexto colombiano.

    Args:
        concept: Concepto a explicar (ej: CDT, UVT, GMF, retención, renta, fiducia, etc.).
    """
    key = concept.lower().strip()

    # Exact match first
    if key in CONCEPTS:
        explanation = CONCEPTS[key]
    else:
        # Fuzzy: find first concept that contains the query
        match = next((v for k, v in CONCEPTS.items() if key in k or k in k.split()), None)
        if not match:
            available = ", ".join(CONCEPTS.keys())
            return (
                f"No tengo información sobre '{concept}'.\n"
                f"Conceptos disponibles: {available}"
            )
        explanation = match

    return (
        f"📚 {concept.upper()}\n\n{explanation}\n\n"
        "⚠️ Esta es información educativa general. Consulta un asesor certificado "
        "para decisiones financieras personales."
    )
