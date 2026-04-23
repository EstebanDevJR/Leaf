"""Servicio de alertas proactivas DIAN — monitorea condiciones y crea alertas."""

import calendar
import logging
from datetime import date, datetime, timedelta

from sqlmodel import Session, func, select

from backend.db.database import engine
from backend.models.alert import Alert
from backend.models.transaction import Transaction, TransactionType
from backend.tools.get_uvt import get_uvt

logger = logging.getLogger(__name__)

# DIAN 2025 renta deadlines (last digit of NIT)
FECHAS_RENTA_2025 = {
    "0": date(2026, 4, 9), "1": date(2026, 4, 14), "2": date(2026, 4, 16),
    "3": date(2026, 4, 21), "4": date(2026, 4, 23), "5": date(2026, 4, 28),
    "6": date(2026, 4, 30), "7": date(2026, 5, 6), "8": date(2026, 5, 8),
    "9": date(2026, 5, 13),
}


def _alert_exists(session: Session, alert_type: str, since: datetime) -> bool:
    """Returns True if an alert of this type was already created since `since`."""
    return bool(
        session.exec(
            select(Alert)
            .where(Alert.type == alert_type)
            .where(Alert.triggered_at >= since)
        ).first()
    )


def _create_alert(
    session: Session,
    type: str,
    severity: str,
    message: str,
    detail: str = "",
) -> Alert:
    alert = Alert(type=type, severity=severity, message=message, detail=detail)
    session.add(alert)
    session.commit()
    session.refresh(alert)
    logger.info("Alert created: [%s] %s", type, message)
    return alert


def check_income_threshold() -> list[Alert]:
    """Trigger: ingresos cruzan el tope de 1.400 UVT en el año en curso."""
    today = date.today()
    uvt = get_uvt(today.year)
    tope = 1_400 * uvt
    start = date(today.year, 1, 1)
    created = []

    with Session(engine) as session:
        total_income = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.type == TransactionType.income)
                .where(Transaction.date >= str(start))
            ).one()
            or 0
        )

        if total_income > tope:
            # Only alert once per year
            year_start = datetime(today.year, 1, 1)
            if not _alert_exists(session, "income_threshold", year_start):
                alert = _create_alert(
                    session,
                    type="income_threshold",
                    severity="warn",
                    message=f"Superaste {1_400:,} UVT de ingresos en {today.year}",
                    detail=(
                        f"Ingresos acumulados: ${total_income:,.0f}\n"
                        f"Tope 1.400 UVT:      ${tope:,.0f}\n\n"
                        "Estás obligado a declarar renta. "
                        "Dile a Leaf: 'genera mi borrador de renta' para ver un resumen."
                    ),
                )
                created.append(alert)
    return created


def check_deadline_alerts(nit_sufijo: str = "") -> list[Alert]:
    """Trigger: 30 y 7 días antes de la fecha límite de declaración de renta."""
    today = date.today()
    created = []

    digito = nit_sufijo.strip()[-1] if nit_sufijo else None
    if not digito:
        return created

    deadline = FECHAS_RENTA_2025.get(digito)
    if not deadline:
        return created

    days_left = (deadline - today).days
    if days_left not in (30, 7):
        return created

    severity = "urgent" if days_left == 7 else "warn"
    window_start = datetime.utcnow() - timedelta(days=2)

    with Session(engine) as session:
        if not _alert_exists(session, f"deadline_{days_left}d", window_start):
            alert = _create_alert(
                session,
                type=f"deadline_{days_left}d",
                severity=severity,
                message=f"Declaración de renta vence en {days_left} días",
                detail=(
                    f"Fecha límite (NIT …{digito}): {deadline.strftime('%d de %B de %Y')}\n\n"
                    "Dile a Leaf: 'genera mi borrador de renta' para prepararte."
                ),
            )
            created.append(alert)
    return created


def check_gmf_monthly() -> list[Alert]:
    """Trigger: resumen GMF al fin de mes."""
    today = date.today()
    # Only run on the last 3 days of the month
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    if today.day < days_in_month - 2:
        return []

    start = date(today.year, today.month, 1)
    created: list[Alert] = []
    window_start = datetime(today.year, today.month, 1)

    with Session(engine) as session:
        if _alert_exists(session, "gmf_monthly", window_start):
            return created

        total_txs = (
            session.exec(
                select(func.sum(Transaction.amount))
                .where(Transaction.date >= str(start))
            ).one()
            or 0
        )

        if total_txs > 0:
            gmf_est = total_txs * 0.004
            deduccion = gmf_est * 0.5
            alert = _create_alert(
                session,
                type="gmf_monthly",
                severity="info",
                message=f"GMF estimado este mes: ${gmf_est:,.0f}",
                detail=(
                    f"Movimientos registrados: ${total_txs:,.0f}\n"
                    f"GMF estimado (0.4%):     ${gmf_est:,.0f}\n"
                    f"Deducible en renta (50%): ${deduccion:,.0f}\n\n"
                    "Guarda tus extractos bancarios para el GMF real."
                ),
            )
            created.append(alert)
    return created


def check_all(nit_sufijo: str = "") -> list[Alert]:
    """Ejecuta todas las verificaciones de alertas."""
    alerts = []
    try:
        alerts += check_income_threshold()
    except Exception as e:
        logger.warning("check_income_threshold failed: %s", e)
    try:
        alerts += check_deadline_alerts(nit_sufijo)
    except Exception as e:
        logger.warning("check_deadline_alerts failed: %s", e)
    try:
        alerts += check_gmf_monthly()
    except Exception as e:
        logger.warning("check_gmf_monthly failed: %s", e)
    return alerts
