"""
Internal, non-public endpoint(s) — not part of the user-facing API surface.

`GET /internal/tasks/heartbeat` replaces the old Celery beat schedule (see
app/worker/tasks.py's module docstring): with no separate worker/beat
process on this deployment, an external uptime pinger (UptimeRobot) hits
this endpoint roughly every few minutes, and it runs the actual scheduled
jobs (dispatch_due_reminders / escalate_overdue_document_requests /
expire_subscriptions) only when enough wall-clock time has actually passed
since the last run — tracked durably in the `system_state` table (see
app/models/system_state.py) so a redeploy or cold start doesn't reset an
in-memory timer and cause the jobs to fire on every restart.

This is under `/internal` and gated on a shared secret specifically so it
is NOT the same thing UptimeRobot would hit for a plain liveness check —
`GET /health` (app/main.py) still exists, unauthenticated, for that.

The secret can be sent either as an `X-Internal-Task-Secret` header or as
a `?secret=...` query parameter — both are checked, whichever is present.
Custom HTTP headers are a paid-tier-only feature on some uptime monitors
(e.g. UptimeRobot's free plan doesn't support them), so the query-param
form exists specifically so this works on a free monitoring plan. The
tradeoff, knowingly accepted: a URL is more likely to end up somewhere
incidental (browser history if opened manually, a proxy's access log) than
a header is — acceptable here since the only thing this secret gates is
triggering already-idempotent, non-destructive scheduled jobs a bit early,
not access to any actual data.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query, status
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.system_state import SystemState
from app.worker.tasks import (
    dispatch_due_reminders,
    escalate_overdue_document_requests,
    expire_subscriptions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

_LAST_RUN_KEY = "last_scheduled_run_at"
# Slightly under the ~hourly cadence the old Celery beat schedule used, so
# an UptimeRobot monitor polling every few minutes will reliably trigger a
# run once an hour has actually passed, without ever running twice within
# the same hour due to poll-timing jitter.
_MIN_INTERVAL = timedelta(minutes=55)


def _check_secret(header_secret: str | None, query_secret: str | None) -> None:
    """No safe default: if INTERNAL_TASK_SECRET isn't configured, every
    request is rejected rather than silently trusted — this endpoint runs
    real scheduled jobs and must never be publicly triggerable."""
    provided = header_secret or query_secret
    if not settings.INTERNAL_TASK_SECRET or provided != settings.INTERNAL_TASK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid task secret (X-Internal-Task-Secret header or ?secret= query param)",
        )


@router.get("/tasks/heartbeat")
@router.head("/tasks/heartbeat")
def tasks_heartbeat(
    x_internal_task_secret: str | None = Header(default=None, alias="X-Internal-Task-Secret"),
    secret: str | None = Query(default=None),
):
    _check_secret(x_internal_task_secret, secret)

    db = SessionLocal()
    try:
        row = db.get(SystemState, _LAST_RUN_KEY)
        now = datetime.now(timezone.utc)

        if row is not None:
            try:
                last_run = datetime.fromisoformat(row.value)
            except ValueError:
                last_run = None
            if last_run is not None and (now - last_run) < _MIN_INTERVAL:
                return {"status": "ok"}

        logger.info("[internal:heartbeat] running scheduled jobs")
        results = {
            "dispatch_due_reminders": dispatch_due_reminders(),
            "escalate_overdue_document_requests": escalate_overdue_document_requests(),
            "expire_subscriptions": expire_subscriptions(),
        }

        if row is None:
            row = SystemState(key=_LAST_RUN_KEY, value=now.isoformat())
            db.add(row)
        else:
            row.value = now.isoformat()
        db.commit()

        return {"status": "ok", "ran_scheduled_jobs": True, "results": results}
    finally:
        db.close()
