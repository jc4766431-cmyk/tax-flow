"""
Tiny key/value settings table for state that must survive process restarts
and cold starts but doesn't belong to any business entity.

First (and currently only) use: `last_scheduled_run_at`, tracking when
GET /internal/tasks/heartbeat last ran the scheduled jobs that used to be a
Celery beat schedule (dispatch_due_reminders / escalate_overdue_document_
requests / expire_subscriptions) — see app/api/v1/endpoints/internal.py.
A single free-tier web instance with no separate worker/beat process has no
safe place to hold this in memory (it would reset on every deploy, restart,
or cold start, causing the heartbeat to re-run the jobs immediately after
every restart instead of respecting the ~hourly cadence).

A generic key/value table (rather than a dedicated single-row
`last_scheduled_run_at` table) so any future "one durable value that isn't
really a business model" need can reuse this rather than growing a new
one-off table each time.
"""
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SystemState(Base):
    __tablename__ = "system_state"

    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(1000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
