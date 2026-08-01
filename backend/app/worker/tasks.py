"""
Background work powering the Automation Center:
  - scheduled deadline reminders (email/WhatsApp/SMS)
  - missing-document follow-ups and escalation
  - OCR + AI field extraction on newly uploaded documents

These used to be Celery tasks backed by a Redis broker. Per the deliberate
"stay on free tiers, minimize moving pieces" decision for this deployment,
Celery/Redis have been removed entirely: these are now plain importable
Python functions, invoked two ways:
  - `dispatch_due_reminders` / `escalate_overdue_document_requests` /
    `expire_subscriptions`: run synchronously from the
    `GET /internal/tasks/heartbeat` endpoint (see
    app/api/v1/endpoints/internal.py), which an external uptime pinger
    (e.g. UptimeRobot) hits roughly hourly. There is no dedicated worker
    process/dyno for these — they run inline on the same web instance,
    inside that one request.
  - `process_document_ocr`: invoked via FastAPI's `BackgroundTasks` right
    after the request that registers a new Document (see
    document_service.py), so OCR runs after the response is sent but still
    inside the same web process — see that module's docstring for the
    accepted risk this carries on a small free-tier instance.
"""
import logging
from datetime import date, datetime, timezone

from sqlalchemy import func, select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.client import Client
from app.models.document import ChecklistItem, DocumentStatus
from app.models.filing import FilingRequest
from app.models.user import User, UserRole
from app.models.workflow import Notification, NotificationType, Reminder, ReminderChannel
from app.models.document import Document
from app.services.billing_service import process_subscription_period_rollovers
from app.services.notification_channels import EmailSender, SMSSender, WhatsAppBusinessAPISender
from app.services.ocr_service import confidence_for, extract_fields, extract_text
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

# After this many follow-ups already sent for a filing, also notify Firm Admins.
ESCALATION_FOLLOWUP_THRESHOLD = 3

_SENDERS = {
    ReminderChannel.EMAIL: EmailSender(),
    ReminderChannel.WHATSAPP: WhatsAppBusinessAPISender(),
    ReminderChannel.SMS: SMSSender(),
}


def _contact_for(channel: ReminderChannel, user: User) -> str | None:
    return user.email if channel == ReminderChannel.EMAIL else user.phone


def dispatch_due_reminders() -> dict:
    """
    Finds Reminder rows whose (filing due_date - days_before_deadline) is today,
    have not been sent, and are not cancelled, then dispatches via the configured
    channel (email/WhatsApp/SMS) and marks sent_at.

    Reminders are auto-cancelled elsewhere (see filings.update_stage / documents
    service) once required documents are received.
    """
    db = SessionLocal()
    sent = 0
    try:
        rows = db.execute(
            select(Reminder, FilingRequest, Client)
            .join(FilingRequest, FilingRequest.id == Reminder.filing_request_id)
            .join(Client, Client.id == FilingRequest.client_id)
            .where(Reminder.sent_at.is_(None), Reminder.cancelled.is_(False),
                   FilingRequest.due_date.is_not(None))
        ).all()

        for reminder, filing, client in rows:
            days_until_due = (filing.due_date - date.today()).days
            if days_until_due != reminder.days_before_deadline:
                continue

            user = db.get(User, client.user_id)
            contact = _contact_for(reminder.channel, user) if user else None
            body = (
                f"Reminder: your {filing.filing_type.value.replace('_', ' ')} "
                f"({filing.period_label or ''}) is due on {filing.due_date.isoformat()}."
            )
            if contact:
                _SENDERS[reminder.channel].send_text(contact, body)

            if user:
                db.add(Notification(
                    user_id=user.id,
                    type=NotificationType.DEADLINE_REMINDER,
                    title="Filing deadline reminder",
                    body=body,
                ))

            reminder.sent_at = datetime.now(timezone.utc)
            db.add(reminder)
            sent += 1

        db.commit()
        return {"sent": sent}
    finally:
        db.close()


def escalate_overdue_document_requests() -> dict:
    """
    For each Client with MISSING documents past the requested checklist deadline:
      1. Send a follow-up notification to the client
      2. Notify the assigned accountant
      3. After ESCALATION_FOLLOWUP_THRESHOLD follow-ups, flag as escalated for Firm Admin review
    Same "past-due missing checklist item" grouping as
    automation.list_escalations (§2e), reused here for dispatch instead of display.
    """
    db = SessionLocal()
    escalated = 0
    try:
        rows = db.execute(
            select(Client, FilingRequest)
            .join(FilingRequest, FilingRequest.client_id == Client.id)
            .join(ChecklistItem, ChecklistItem.filing_request_id == FilingRequest.id)
            .where(
                ChecklistItem.status == DocumentStatus.MISSING,
                FilingRequest.due_date.is_not(None),
                FilingRequest.due_date < date.today(),
            )
            .distinct()
        ).all()

        for client, filing in rows:
            prior_followups = db.scalar(
                select(func.count()).select_from(Notification).where(
                    Notification.type == NotificationType.MISSING_DOCUMENT,
                    Notification.link_url == f"/filings/{filing.id}",
                )
            ) or 0

            body = (
                f"Documents are still missing for your {filing.filing_type.value.replace('_', ' ')} "
                f"(due {filing.due_date.isoformat()})."
            )
            client_user = db.get(User, client.user_id)
            if client_user:
                db.add(Notification(
                    user_id=client_user.id, type=NotificationType.MISSING_DOCUMENT,
                    title="Missing documents", body=body, link_url=f"/filings/{filing.id}",
                ))

            accountant_id = filing.assigned_accountant_id or client.assigned_accountant_id
            if accountant_id:
                db.add(Notification(
                    user_id=accountant_id, type=NotificationType.MISSING_DOCUMENT,
                    title=f"Client documents overdue: {client.company_name or client.id}",
                    body=body, link_url=f"/filings/{filing.id}",
                ))

            if prior_followups + 1 >= ESCALATION_FOLLOWUP_THRESHOLD:
                admins = db.scalars(
                    select(User).where(User.firm_id == client.firm_id, User.role == UserRole.FIRM_ADMIN)
                ).all()
                for admin in admins:
                    db.add(Notification(
                        user_id=admin.id, type=NotificationType.MISSING_DOCUMENT,
                        title=f"Escalated: overdue documents for {client.company_name or client.id}",
                        body=body, link_url=f"/filings/{filing.id}",
                    ))
                escalated += 1

        db.commit()
        return {"escalated": escalated}
    finally:
        db.close()


def process_document_ocr(document_id: str) -> dict:
    """
    Runs OCR (Tesseract, or Google Document AI if configured) against a newly
    uploaded document, classifies its type, extracts structured fields
    (PAN, GSTIN, invoice totals, names, dates), and stores extraction_confidence
    + extracted_fields on the Document row for the review UI to display.

    Runs via FastAPI BackgroundTasks on the same process/instance that also
    serves API requests (no separate worker — see this module's docstring),
    so it's a known, accepted risk on a small free-tier instance. To keep
    that risk bounded: documents above OCR_MAX_FILE_SIZE_MB are skipped
    (logged, not crashed — see extract_text/ocr_service.py for the lowered
    render DPI, the other half of this mitigation).
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return {"document_id": document_id, "status": "not_found"}

        max_bytes = settings.OCR_MAX_FILE_SIZE_MB * 1024 * 1024
        if document.file_size_bytes and document.file_size_bytes > max_bytes:
            logger.info(
                f"[ocr:skipped] document {document_id} is "
                f"{document.file_size_bytes} bytes, over the "
                f"{settings.OCR_MAX_FILE_SIZE_MB}MB auto-OCR threshold — "
                "skipping (not crashing). Can still be reviewed manually."
            )
            return {"document_id": document_id, "status": "skipped_too_large"}

        file_bytes = storage_service.download_bytes(document.storage_key)
        text = extract_text(file_bytes, document.mime_type)
        fields = extract_fields(text)

        document.ocr_text = text or None
        document.extracted_fields = fields or None
        document.extraction_confidence = confidence_for(text, fields)
        db.commit()
        return {"document_id": document_id, "status": "processed", "fields": fields}
    finally:
        db.close()


def expire_subscriptions() -> dict:
    """Cancels subscriptions with cancel_at_period_end set, and marks other
    subscriptions past their current_period_end as PAST_DUE (no gateway to
    confirm a renewal charge). See billing_service.
    process_subscription_period_rollovers for the actual logic.
    """
    db = SessionLocal()
    try:
        return process_subscription_period_rollovers(db)
    finally:
        db.close()
