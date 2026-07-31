"""
Celery application for async background work: deadline reminder dispatch,
missing-document escalation, and OCR/document-extraction processing.
"""
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "taxflow",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "dispatch-deadline-reminders": {
            "task": "app.worker.tasks.dispatch_due_reminders",
            "schedule": 3600.0,  # hourly
        },
        "escalate-overdue-documents": {
            "task": "app.worker.tasks.escalate_overdue_document_requests",
            "schedule": 3600.0,
        },
        "expire-subscriptions": {
            "task": "app.worker.tasks.expire_subscriptions",
            "schedule": 3600.0,  # hourly; date-only granularity so this is idempotent
        },
    },
)
