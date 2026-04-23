from langchain_core.tools import tool

CONCEPTS: dict[str, str] = {
    "cdt": (
        "Un CDT (Certificado de Depósito a Término) es un producto de ahorro bancario donde depositas "
        "dinero por un plazo fijo (3, 6, 12 o 24 meses) y el banco te paga una tasa de interés acordada.\n\n"
        "Cómo funciona:\n"
        "  • Depositas un monto mínimo (usualmente $1.000.000 COP).\n"
        "  • El banco te garantiza una tasa EA (efectiva anual) fija.\n"
        "  • Al vencer el plazo, recibes el capital + intereses menos retención (7%).\n"
        "  • No puedes retirar antes sin penalización.\n\n"
        "Ventajas: seguro (FOGAFÍN cubre hasta $50M por entidad), sin riesgo de mercado.\n"
        "Desventaja: ilíquido durante el plazo.\n\n"
        "Tip: pregúntame '¿dónde invierto $X a Y meses?' para ver las mejores tasas de hoy."
    ),
    "uvt": (
        "La UVT (Unidad de Valor Tributario) es la unidad que usa la DIAN para expresar "
        "montos tributarios actualizados con la inflación.\n\n"
        "Valores: 2024: $47.065 | 2025: $49.799 | 2026: ~$52.000 COP (provisional)\n\n"
        "Se usa para calcular:\n"
        "  • Topes de obligación de declarar renta (1.400 UVT)\n"
        "  • Rangos del impuesto de renta (tabla marginal)\n"
        "  • Topes de deducción (salud, vivienda, etc.)\n"
        "  • Retención en la fuente para asalariados"
    ),
    "gmf": (
        "El GMF (Gravamen a los Movimientos Financieros) o '4×1000' es un impuesto del 0.4% "
        "que se cobra sobre cada transacción bancaria en Colombia.\n\n"
        "Lo descuenta automáticamente tu banco en cada retiro o transferencia.\n\n"
        "Dato clave: el 50% de lo pagado es deducible en tu declaración de renta, "
        "pero solo si tienes cuenta de ahorros exenta designada.\n\n"
        "Tip: muchos bancos ofrecen una cuenta de ahorros exenta de GMF — úsala para movimientos frecuentes."
    ),
    "retencion": (
        "La retención en la fuente es un anticipo del impuesto de renta que te descuentan "
        "cuando recibes pagos.\n\n"
        "Para empleados (asalariados):\n"
        "  • Se calcula sobre el sueldo neto menos deducciones (salud, pensión, exención 25%)\n"
        "  • Tasa marginal: 0% hasta ~$4.5M/mes, 19% entre $4.5M-$7M, 28%+ por encima\n\n"
        "Para independientes/freelancers:\n"
        "  • Honorarios: ~10-11% | Servicios: ~4-6% | Consultoría: ~10%\n\n"
        "No es un impuesto adicional — es un descuento anticipado que se cruza con tu "
        "declaración de renta al final del año."
    ),
    "renta": (
        "El impuesto de renta es un tributo anual sobre tus ingresos.\n\n"
        "Debes declarar si en 2026 tuviste:\n"
        "  • Ingresos brutos > 1.400 UVT (~$72.8M)\n"
        "  • Patrimonio bruto > 4.500 UVT (~$234M)\n"
        "  • Consumos con tarjeta > 1.400 UVT\n\n"
        "Tasas progresivas: desde 0% hasta 39% según renta líquida gravable.\n"
        "Leaf puede estimarlo con 'calcula mi impuesto de renta'."
    ),
    "fiducia": (
        "Una fiducia (o fondo de inversión colectiva — FIC) es un vehículo donde varios inversionistas "
        "juntan capital y una fiduciaria lo gestiona invirtiendo en renta fija, acciones u otros activos.\n\n"
        "Tipos comunes en Colombia:\n"
        "  • Fiducia de renta fija: bajo riesgo, liquidez diaria, ~9-12% EA\n"
        "  • Fondo en acciones: mayor riesgo y potencial de ganancia\n\n"
        "Ventaja vs CDT: más liquidez. Desventaja: tasa variable."
    ),
    "fondo de emergencia": (
        "El fondo de emergencia es un colchón de ahorro líquido para cubrir imprevistos "
        "sin endeudarse.\n\n"
        "Regla para Colombia: entre 4 y 6 meses de tus gastos mensuales (mayor que en otros países "
        "por la volatilidad económica).\n\n"
        "Ejemplo: si gastas $2.000.000/mes, tu fondo debe ser entre $8M y $12M.\n\n"
        "Dónde guardarlo: cuenta de ahorros de alta rentabilidad o CDT a corto plazo — "
        "accesible pero separado de tu cuenta corriente."
    ),
    "presupuesto": (
        "Un presupuesto es un plan de cómo distribuirás tus ingresos entre gastos y ahorro.\n\n"
        "Método popular — regla 50/30/20:\n"
        "  • 50% necesidades (vivienda, comida, transporte)\n"
        "  • 30% deseos (entretenimiento, ropa, ocio)\n"
        "  • 20% ahorro/deuda\n\n"
        "En Leaf puedes configurar límites por categoría: 'establece presupuesto para comida $800.000'."
    ),
    "tasa ea": (
        "La tasa EA (Efectiva Anual) es la tasa de interés real que ganas o pagas en un año, "
        "incluyendo la capitalización.\n\n"
        "Ejemplo: un CDT al 11.5% EA sobre $10.000.000 genera $1.150.000 en 12 meses.\n\n"
        "No confundir con tasa nominal (MV, TV, SV) que no incluye el efecto del interés compuesto. "
        "Siempre compara productos financieros usando la tasa EA."
    ),
    "interes compuesto": (
        "El interés compuesto es cuando los intereses generados se suman al capital y también generan intereses.\n\n"
        "Ejemplo: $1.000.000 al 12% EA compuesto:\n"
        "  • Año 1: $1.120.000\n"
        "  • Año 2: $1.254.400\n"
        "  • Año 5: $1.762.342\n"
        "  • Año 10: $3.105.848\n\n"
        "Einstein lo llamaba 'la octava maravilla del mundo'. Entre más temprano empieces, más crece."
    ),
    "tes": (
        "Los TES (Títulos de Tesorería) son bonos del gobierno colombiano — básicamente le prestas "
        "plata al Estado y él te paga intereses.\n\n"
        "Características:\n"
        "  • Emisor: Ministerio de Hacienda de Colombia\n"
        "  • Riesgo: muy bajo (respaldado por el Estado)\n"
        "  • Tasa: variable, actualmente ~12-14% EA (2026)\n"
        "  • Plazo: 1 a 15 años\n\n"
        "Cómo comprarlos: a través de una comisionista de bolsa o fondos de renta fija. "
        "No se compran directamente en un banco como los CDT."
    ),
    "etf": (
        "Un ETF (Exchange Traded Fund) es un fondo que cotiza en bolsa y replica un índice o sector.\n\n"
        "En Colombia puedes acceder a ETFs internacionales a través de brokers como Ameritrade, "
        "Interactive Brokers o algunas comisionistas locales.\n\n"
        "ETFs populares para colombianos:\n"
        "  • SPY/VOO: replica el S&P 500 (500 empresas más grandes de EE.UU.)\n"
        "  • QQQ: tecnología (Apple, Google, Amazon, etc.)\n"
        "  • VT: mercado global\n\n"
        "Ventaja: diversificación instantánea. Riesgo: volátil, no garantiza retorno."
    ),
    "inflacion": (
        "La inflación es el aumento generalizado de precios con el tiempo — hace que el dinero "
        "compre menos.\n\n"
        "Colombia 2026: inflación ~5.5% anual (proyección)\n\n"
        "Impacto práctico:\n"
        "  • $1.000.000 hoy = $945.000 de poder adquisitivo en 1 año\n"
        "  • Un CDT al 11.5% EA = 6% de ganancia real por encima de la inflación\n\n"
        "Regla de oro: cualquier inversión debe superar la inflación para que valga la pena."
    ),
    "patrimonio neto": (
        "El patrimonio neto (o riqueza neta) es la diferencia entre lo que tienes y lo que debes.\n\n"
        "Fórmula: Activos − Pasivos = Patrimonio Neto\n\n"
        "Ejemplo:\n"
        "  • Activos: ahorros $5M + carro $20M + CDT $10M = $35M\n"
        "  • Pasivos: crédito de vehículo $12M + tarjeta de crédito $2M = $14M\n"
        "  • Patrimonio neto: $35M − $14M = $21M\n\n"
        "Meta: que tu patrimonio neto crezca cada año — señal de salud financiera."
    ),
    "diversificacion": (
        "Diversificar es distribuir tu dinero en diferentes activos para reducir el riesgo.\n\n"
        "Principio: 'No pongas todos los huevos en una canasta'.\n\n"
        "Ejemplo de portafolio diversificado:\n"
        "  • 40% CDT (bajo riesgo, tasa fija)\n"
        "  • 30% Fondos de renta fija (liquidez)\n"
        "  • 20% ETFs internacionales (largo plazo)\n"
        "  • 10% Fondo de emergencia (efectivo)\n\n"
        "Si un activo cae, los otros pueden compensar la pérdida."
    ),
    "fogafin": (
        "FOGAFÍN (Fondo de Garantías de Instituciones Financieras) es el equivalente colombiano "
        "del seguro de depósitos bancarios.\n\n"
        "Protege tus ahorros si un banco quiebra:\n"
        "  • Cubre hasta $50.000.000 COP por persona por entidad\n"
        "  • Aplica a: cuentas de ahorro, CDT, cuentas corrientes\n\n"
        "Tip: si tienes más de $50M en ahorros, distribúyelos en varias entidades."
    ),
    "smmlv": (
        "El SMMLV (Salario Mínimo Mensual Legal Vigente) es el salario mínimo en Colombia.\n\n"
        "Valor 2026: $1.423.500 COP/mes\n"
        "Auxilio de transporte 2026: ~$200.000 COP/mes\n\n"
        "El SMMLV se usa como referencia para:\n"
        "  • Calcular aportes parafiscales\n"
        "  • Topes de fondo de solidaridad pensional\n"
        "  • Comparar niveles de ingreso en el sistema tributario"
    ),
    "pension": (
        "El sistema pensional colombiano tiene dos regímenes:\n\n"
        "1. RPM (Colpensiones — régimen público):\n"
        "  • El Estado administra tu pensión\n"
        "  • Requiere semanas cotizadas (1.300 semanas mínimo)\n"
        "  • Pensión: porcentaje del promedio de tus últimos 10 años\n\n"
        "2. RAIS (fondos privados — Porvenir, Protección, etc.):\n"
        "  • Cuenta individual — acumulas lo que cotizas + rendimientos\n"
        "  • Más flexible si trabajas como independiente\n\n"
        "Aporte total: 16% del salario (12% empleador + 4% empleado)."
    ),
}


@tool
def explain_concept(concept: str) -> str:
    """Explica conceptos financieros en lenguaje simple con contexto colombiano.

    Conceptos disponibles: CDT, UVT, GMF, retención en la fuente, renta, fiducia,
    fondo de emergencia, presupuesto, tasa EA, interés compuesto, TES, ETF,
    inflación, patrimonio neto, diversificación, FOGAFÍN, SMMLV, pensión.

    Args:
        concept: Concepto a explicar (ej: CDT, UVT, inflación, ETF, FOGAFÍN, etc.).
    """
    key = concept.lower().strip()

    # Exact match
    if key in CONCEPTS:
        explanation = CONCEPTS[key]
    else:
        # Fuzzy: find first concept where query is substring or vice versa
        match = next(
            (v for k, v in CONCEPTS.items() if key in k or k in key or any(w in k for w in key.split())),
            None,
        )
        if not match:
            available = ", ".join(CONCEPTS.keys())
            return (
                f"No tengo información sobre '{concept}'.\n"
                f"Conceptos disponibles: {available}\n\n"
                "También puedes preguntarme directamente y trataré de explicártelo."
            )
        explanation = match

    return (
        f"📚 {concept.upper()}\n\n{explanation}\n\n"
        "⚠️ Esta es información educativa general. Consulta un asesor certificado "
        "para decisiones financieras personales."
    )
