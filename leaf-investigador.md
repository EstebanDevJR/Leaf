# Leaf — Agente Investigador Financiero

Un agente autónomo que observa patrones de gasto, detecta oportunidades de ahorro y educa financieramente al usuario sin necesidad de que este lo invoque primero.

## Propuesta de valor

- Los demás agentes de Leaf son reactivos; el Investigador corre en segundo plano y actúa cuando detecta algo relevante.
- Tiene toggle ON/OFF:
  - OFF: no consume recursos ni interrumpe.
  - ON: monitoreo continuo y alertas oportunas.

## Modos del Investigador

1. **Observación pasiva**
   - Registra patrones sin interrumpir.
   - Construye perfil financiero en background.
2. **Alerta de hábito**
   - Detecta anomalías de gasto.
   - Notifica antes de que escalen.
3. **Investigación activa**
   - Analiza una categoría o período puntual.
   - Entrega informe de hallazgos.
4. **Meta de ahorro**
   - Proyecta cuándo se alcanza una meta.
   - Recalcula según cambios de comportamiento.

## Cómo encaja en Leaf (arquitectura)

### Triggers de entrada

- Scheduler diario (`cron`, 08:00)
- Evento de nueva transacción
- Solicitud explícita del usuario (`"analiza mis gastos"`)

### Núcleo

- **Agente Investigador** (LangGraph, autónomo, con toggle ON/OFF)

### Fuentes de datos

- SQLite (historial de transacciones)
- Perfil financiero (memoria persistente)
- Contexto colombiano (UVT, tasas CDT)

### Canales de salida

- Alerta por OpenClaw (WhatsApp/Telegram)
- Informe en UI (dashboard SvelteKit)
- Respuesta en chat cuando el usuario pregunta

## Ejemplo de uso real (conversación)

- El agente detecta un aumento inusual en delivery:
  - `$340.000` vs `$89.000` del mes anterior.
  - `+282%` en 18 días.
  - Proyección de cierre: `$567.000` (19% del presupuesto de comida).
- Ante la pregunta de ahorro potencial:
  - Mercado promedio: `$180.000/mes`
  - Delivery promedio: `$210.000/mes`
  - Reduciendo delivery a 4 pedidos/mes (`~$80.000`) ahorraría:
    - `$130.000/mes`
    - `$1.560.000/año`
  - El fondo de emergencia llegaría a 3 meses en 7 meses (vs 11).
- Hallazgos adicionales en 90 días:
  - Suscripciones duplicadas (`$89.000/mes`, bajo uso en algunas).
  - Picos de ocio en viernes (67% del gasto de ocio; 2.3x mayor).
  - Dinero inactivo (`$1.200.000`) con oportunidad de CDT (`~11.5% EA`).
- También responde educación financiera (ejemplo: qué es un CDT y cómo funciona).

## Tools del Investigador

- `analyze_patterns()` — tendencias por categoría/período.
- `detect_anomaly()` — compara gasto actual vs histórico y alerta por umbral.
- `find_subscriptions()` — identifica pagos recurrentes/suscripciones.
- `calculate_savings_goal()` — proyecta tiempo para meta de ahorro.
- `get_cdt_rates()` — consulta tasas CDT en bancos colombianos (uso educativo).
- `analyze_weekday()` — distribuye gasto por día de semana.
- `find_idle_money()` — detecta saldos sin movimiento por N días.
- `emergency_fund_status()` — calcula cobertura en meses de gastos.
- `generate_insight_report()` — consolida hallazgos en informe legible.
- `explain_concept()` — educación financiera en lenguaje simple.

## Cuándo actúa sin que el usuario pida nada

- **Cada transacción**: evalúa anomalías o exceso de presupuesto (`detect_anomaly()`, tiempo real).
- **08:00 diario**: revisa dinero inactivo >30 días (`find_idle_money()`), silencioso hasta umbral.
- **Día 15**: proyecta cierre de mes (`analyze_patterns()`), alerta si la proyección es negativa.
- **Fin de mes**: genera informe completo (`generate_insight_report()`).
- **Trimestral**: análisis profundo de 90 días (`analyze_patterns(period=90d)`).

## Implementación base (resumen técnico)

### `backend/agents/investigador.py`

- Define `TriggerType`:
  - `NUEVA_TX`
  - `SCHEDULER`
  - `FIN_DE_MES`
  - `USUARIO_PIDE`
- Define `InvestigadorState` (Pydantic):
  - `trigger`, `user_id`, `enabled`
  - `anomalias`, `insights`, `alertas`
  - `debe_notificar`
- Router `check_enabled()`:
  - Si toggle OFF -> `fin`
  - Si ON -> `analizar`
- Lógica de anomalías `detect_anomaly()`:
  - Compara gasto de 30 días vs promedio histórico 3 meses.
  - Marca anomalía si supera 50% del promedio.
- Lógica de dinero inactivo `find_idle_money()`:
  - Busca wallets sin movimiento >30 días.
  - Genera insight si balance supera umbral (`500_000`).
- Construye grafo LangGraph:
  - `check_enabled -> analizar -> idle_money -> notificar -> fin`

### `backend/scheduler.py`

- Usa `APScheduler` (`AsyncIOScheduler`).
- Job diario `08:00` (`daily_analysis`):
  - Itera usuarios activos.
  - Invoca el grafo con trigger `SCHEDULER`.
- Hook por nueva transacción (`on_new_transaction`):
  - Invoca el grafo con trigger `NUEVA_TX`.
  - Respeta estado del toggle del usuario.

## Límite legal (obligatorio)

Cuando el agente menciona tasas, instrumentos financieros o datos de mercado, se agrega automáticamente:

> "Esta es información educativa, no asesoría de inversión. Consulta un asesor certificado para decisiones financieras."

Este disclaimer es parte obligatoria del pipeline del agente, no del LLM.

## Nota de diseño

- Versión de diseño: `v1`
- Enfoque operativo: `APScheduler`, sin Redis.
