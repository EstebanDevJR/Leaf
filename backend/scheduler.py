"""Scheduler del Agente Investigador — job diario 08:00 + hook por nueva transacción."""

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_scheduler_task: asyncio.Task | None = None


def _seconds_until_next_8am() -> float:
    """Calcula los segundos hasta las 08:00 del día siguiente (o hoy si aún no ha pasado)."""
    now = datetime.now()
    target = now.replace(hour=8, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _daily_analysis():
    """Job diario: espera hasta las 08:00 y ejecuta el análisis del Investigador."""
    from backend.agents.investigador import TriggerType, run_investigador

    # Wait until 08:00 the first time
    delay = _seconds_until_next_8am()
    logger.info("Investigador: próximo análisis diario en %.0f segundos", delay)
    await asyncio.sleep(delay)

    while True:
        try:
            logger.info("Investigador: ejecutando análisis diario 08:00")
            result = run_investigador(trigger=TriggerType.SCHEDULER, user_id="local")
            if result.alertas:
                logger.info("Investigador: %d alertas creadas", len(result.alertas))
        except Exception as e:
            logger.warning("Investigador daily analysis failed: %s", e)

        # Sleep until next 08:00
        await asyncio.sleep(_seconds_until_next_8am())


def start_scheduler() -> asyncio.Task:
    """Inicia el scheduler del Investigador como tarea asyncio. Retorna la tarea."""
    global _scheduler_task
    _scheduler_task = asyncio.create_task(_daily_analysis())
    logger.info("Investigador scheduler iniciado")
    return _scheduler_task


def stop_scheduler():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        _scheduler_task = None


def on_new_transaction(user_id: str = "local"):
    """Hook síncrono: lanza el análisis del Investigador en background ante nueva transacción."""
    from backend.agents.investigador import TriggerType, run_investigador

    async def _run():
        try:
            result = run_investigador(trigger=TriggerType.NUEVA_TX, user_id=user_id)
            if result.anomalias:
                logger.info(
                    "Investigador (nueva tx): %d anomalías detectadas", len(result.anomalias)
                )
        except Exception as e:
            logger.warning("Investigador on_new_transaction failed: %s", e)

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_run())
    except RuntimeError:
        # No running loop (e.g. in tests) — skip silently
        pass
