from dataclasses import dataclass

THRESHOLDS = {
    "pending_job_warning_age_seconds": 300,
    "pending_job_critical_age_seconds": 1_800,
    "worker_warning_stale_seconds": 75,
    "worker_critical_stale_seconds": 120,
    "worker_critical_consecutive_failures": 3,
    "pending_documents_warning": 20,
    "open_exceptions_warning": 50,
}


@dataclass(frozen=True)
class OperationalMetrics:
    pending_jobs: int = 0
    oldest_pending_job_age_seconds: int | None = None
    open_exceptions: int = 0
    open_critical_incidents: int = 0
    pending_documents: int = 0
    failed_messages: int = 0
    legacy_plaintext_documents: int = 0
    worker_observed: bool = False
    worker_status: str | None = None
    worker_stale_seconds: int | None = None
    worker_consecutive_failures: int = 0


def _alert(
    key: str, severity: str, value: int | str, threshold: int | str, message: str
) -> dict:
    return {
        "key": key,
        "severity": severity,
        "value": value,
        "threshold": threshold,
        "message": message,
    }


def evaluate_operational_health(metrics: OperationalMetrics) -> tuple[str, list[dict]]:
    alerts: list[dict] = []
    if metrics.legacy_plaintext_documents:
        alerts.append(
            _alert(
                "legacy_plaintext_documents",
                "critical",
                metrics.legacy_plaintext_documents,
                0,
                "Hay documentos sin cifrado moderno.",
            )
        )
    if metrics.open_critical_incidents:
        alerts.append(
            _alert(
                "open_critical_incidents",
                "critical",
                metrics.open_critical_incidents,
                0,
                "Hay incidentes críticos abiertos.",
            )
        )
    if metrics.failed_messages:
        alerts.append(
            _alert(
                "failed_messages",
                "warning",
                metrics.failed_messages,
                0,
                "Hay mensajes con entrega fallida.",
            )
        )
    age = metrics.oldest_pending_job_age_seconds
    if age is not None and age >= THRESHOLDS["pending_job_critical_age_seconds"]:
        alerts.append(
            _alert(
                "oldest_pending_job",
                "critical",
                age,
                THRESHOLDS["pending_job_critical_age_seconds"],
                "La cola tiene trabajo pendiente críticamente atrasado.",
            )
        )
    elif age is not None and age >= THRESHOLDS["pending_job_warning_age_seconds"]:
        alerts.append(
            _alert(
                "oldest_pending_job",
                "warning",
                age,
                THRESHOLDS["pending_job_warning_age_seconds"],
                "La cola tiene trabajo pendiente atrasado.",
            )
        )
    if metrics.pending_documents >= THRESHOLDS["pending_documents_warning"]:
        alerts.append(
            _alert(
                "pending_documents",
                "warning",
                metrics.pending_documents,
                THRESHOLDS["pending_documents_warning"],
                "La revisión documental acumula pendientes.",
            )
        )
    if metrics.open_exceptions >= THRESHOLDS["open_exceptions_warning"]:
        alerts.append(
            _alert(
                "open_exceptions",
                "warning",
                metrics.open_exceptions,
                THRESHOLDS["open_exceptions_warning"],
                "La bandeja de excepciones supera el umbral operativo.",
            )
        )
    if not metrics.worker_observed:
        alerts.append(
            _alert(
                "worker_not_observed",
                "critical",
                "missing",
                "observed",
                "El worker todavía no registra actividad.",
            )
        )
    else:
        stale = metrics.worker_stale_seconds or 0
        failures = metrics.worker_consecutive_failures
        if (
            stale >= THRESHOLDS["worker_critical_stale_seconds"]
            or failures >= THRESHOLDS["worker_critical_consecutive_failures"]
        ):
            alerts.append(
                _alert(
                    "worker_degraded",
                    "critical",
                    f"stale={stale}s/failures={failures}",
                    f"stale<{THRESHOLDS['worker_critical_stale_seconds']}s/failures<{THRESHOLDS['worker_critical_consecutive_failures']}",
                    "El worker está detenido o acumula fallos.",
                )
            )
        elif (
            stale >= THRESHOLDS["worker_warning_stale_seconds"]
            or metrics.worker_status == "degraded"
            or failures
        ):
            alerts.append(
                _alert(
                    "worker_degraded",
                    "warning",
                    f"stale={stale}s/failures={failures}",
                    f"stale<{THRESHOLDS['worker_warning_stale_seconds']}s/failures=0",
                    "El worker muestra degradación reciente.",
                )
            )
    severity = (
        "critical"
        if any(item["severity"] == "critical" for item in alerts)
        else ("warning" if alerts else "healthy")
    )
    return severity, alerts


def worker_delay_seconds(
    consecutive_failures: int, *, base_seconds: int = 30, maximum_seconds: int = 300
) -> int:
    """Exponential retry delay; a successful cycle (zero failures) uses the base cadence."""
    exponent = max(0, min(consecutive_failures, 10))
    return min(maximum_seconds, base_seconds * (2**exponent))
