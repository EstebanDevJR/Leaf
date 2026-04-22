# Leaf 🌿

**Agente financiero personal colombiano — local-first, multi-agente, open source.**

Sin nube. Sin suscripciones. Tus datos en tu máquina.

## Inicio rápido

```bash
# 1. Clonar
git clone https://github.com/EstebanDevJR/Leaf.git
cd leaf

# 2. Copiar variables de entorno
cp .env.example .env

# 3. Levantar todo con Docker Compose
docker compose up

# 4. Descargar el modelo LLM (primera vez)
docker compose exec ollama ollama pull gemma4:e4b
```

La app estará en http://localhost:5173 y la API en http://localhost:8000.

## Desarrollo local

### Backend

```bash
# Instalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Instalar dependencias
uv sync

# Correr backend
uv run uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Ollama (LLM local)

```bash
# Instalar Ollama: https://ollama.com
ollama pull gemma4:e4b
```

## Agentes

Leaf tiene cinco agentes especializados orquestados por un ReAct central:

| Agente | Rol |
|--------|-----|
| **Orquestador** | Coordina todos los agentes y responde en chat |
| **Transacciones** | Registra, edita y consulta gastos e ingresos |
| **Insights** | Presupuestos, predicciones y resumen mensual |
| **DIAN** | Impuesto de renta, retención, GMF y fechas límite |
| **OCR** | Extrae datos de recibos con Moondream2 |
| **Investigador** | Monitoreo autónomo en background con toggle ON/OFF |

### Agente Investigador

Corre en segundo plano y actúa sin que el usuario lo pida:

- **08:00 diario** — detecta dinero inactivo y anomalías de gasto.
- **Por cada transacción** — evalúa si el gasto de la categoría es anómalo vs. el historial.
- **Manual** — `POST /investigador/run` para dispararlo en cualquier momento.

Herramientas disponibles también desde el chat:

```
analyze_patterns      tendencias de gasto vs. período anterior
detect_anomaly        alerta si el gasto supera 50% del promedio histórico
find_subscriptions    pagos recurrentes y suscripciones activas
calculate_savings_goal proyección de meta de ahorro con escenarios
get_cdt_rates         tasas CDT de referencia en bancos colombianos
analyze_weekday       distribución de gastos por día de semana
find_idle_money       balance acumulado sin movimiento reciente
emergency_fund_status cobertura del fondo de emergencia en meses
generate_insight_report informe completo de todos los hallazgos
explain_concept       educación financiera (CDT, UVT, GMF, renta…)
```

Toggle ON/OFF via API:

```bash
# Desactivar
curl -X POST http://localhost:8000/investigador/toggle -H "Content-Type: application/json" -d '{"enabled": false}'

# Estado actual
curl http://localhost:8000/investigador/status
```

## Arquitectura

```
leaf/
├── backend/
│   ├── agents/           # Orquestador LangGraph + 5 agentes especializados
│   │   ├── orchestrator.py
│   │   ├── transactions.py
│   │   ├── insights.py
│   │   ├── dian.py
│   │   ├── ocr.py
│   │   └── investigador.py   # StateGraph autónomo con toggle
│   ├── tools/            # 31 herramientas tipadas
│   ├── api/routes/       # FastAPI routes (chat, transactions, budgets, alerts, investigador, ocr)
│   ├── services/         # Alert checker DIAN (12 h)
│   ├── scheduler.py      # Job diario 08:00 + hook on_new_transaction
│   ├── db/               # SQLite engine + session
│   └── models/           # SQLModel (Transaction, Budget, Alert, InvestigadorConfig)
├── frontend/             # SvelteKit + Svelte 5
├── openclaw-skill/       # Skill para OpenClaw (WhatsApp / Telegram)
└── docker-compose.yml
```

## Stack

| Capa | Tecnología |
|------|------------|
| Agentes | LangGraph |
| LLM | Ollama + gemma4 |
| API | FastAPI + Python 3.11 |
| ORM | SQLModel |
| DB | SQLite |
| Frontend | SvelteKit + Svelte 5 |
| Paquetes | uv |
| Infra | Docker Compose |

## API

```
POST   /chat/stream              chat con streaming SSE
GET    /transactions/            historial de transacciones
GET    /transactions/stats       resumen mensual (ingresos, gastos, balance)
POST   /transactions/            crear transacción
PATCH  /transactions/{id}        editar transacción
DELETE /transactions/{id}        eliminar transacción
GET    /budgets/                 listar presupuestos
PUT    /budgets/{category}       crear/actualizar presupuesto
GET    /alerts/                  alertas activas
POST   /alerts/{id}/dismiss      descartar alerta
POST   /ocr/extract              extraer datos de recibo (imagen)
GET    /investigador/status      estado del toggle
POST   /investigador/toggle      activar / desactivar Investigador
POST   /investigador/run         disparar análisis manual
GET    /health                   estado del servicio
```

## Roadmap

- [x] **Fase 1** — Core: orquestador + transacciones + SQLite + FastAPI + SvelteKit
- [x] **Fase 2** — OCR de recibos (Moondream2)
- [x] **Fase 3** — Insights + presupuestos
- [x] **Fase 4** — Skill de OpenClaw (WhatsApp / Telegram)
- [x] **Fase 5** — Reportes DIAN
- [x] **Fase 6** — Agente Investigador autónomo (monitoreo en background, 10 herramientas de análisis)

## Contribuir

Lee [CONTRIBUTING.md](CONTRIBUTING.md).

---

*Leaf 🌿 — hecho en Colombia, para el mundo.*
