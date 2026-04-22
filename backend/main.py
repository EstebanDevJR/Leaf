import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import chat, ocr, transactions
from backend.api.routes import alerts, budgets
from backend.api.routes import investigador as investigador_router
from backend.db.database import create_tables
from backend.models import alert as _alert_model  # noqa: F401 — registers table
from backend.models import budget as _budget_model  # noqa: F401 — registers table
from backend.models import investigador_config as _inv_config_model  # noqa: F401 — registers table

logger = logging.getLogger(__name__)

_checker_task: asyncio.Task | None = None


async def _periodic_alert_check():
    """Runs alert checks every 12 hours."""
    from backend.services.alert_checker import check_all
    while True:
        try:
            new_alerts = check_all()
            if new_alerts:
                logger.info("Proactive alerts created: %d", len(new_alerts))
        except Exception as e:
            logger.warning("Alert check failed: %s", e)
        await asyncio.sleep(12 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    global _checker_task
    _checker_task = asyncio.create_task(_periodic_alert_check())

    from backend.scheduler import start_scheduler, stop_scheduler
    start_scheduler()

    yield

    if _checker_task:
        _checker_task.cancel()
    stop_scheduler()


app = FastAPI(
    title="Leaf API",
    description="Agente financiero personal colombiano — local-first",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
app.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
app.include_router(budgets.router, prefix="/budgets", tags=["budgets"])
app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
app.include_router(investigador_router.router, prefix="/investigador", tags=["investigador"])


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "leaf", "version": "2.0.0"}
