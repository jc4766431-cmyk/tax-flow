"""
Background tasks powering the Automation Center:
  - scheduled deadline reminders (email/WhatsApp/SMS)
  - missing-document follow-ups and escalation
  - OCR + AI field extraction on newly uploaded documents

These are structured so each concern has a single-responsibility task that
can be tested, retried, and monitored independently.
"""
from datetime import date, datetime, timezone

from celery import shared_task
from sqlalchemy import func, select

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
from app.worker.celery_app import celery_app

# After this many follow-ups already sent for a filing, also notify Firm Admins.
ESCALATION_FOLLOWUP_THRESHOLD = 3

_SENDERS = {
    ReminderChannel.EMAIL: EmailSender(),
    ReminderChannel.WHATSAPP: WhatsAppBusinessAPISender(),
    ReminderChannel.SMS: SMSSender(),
}


def _contact_for(channel: ReminderChannel, user: User) -> str | None:
    return user.email if channel == ReminderChannel.EMAIL else user.phone


@celery_app.task(name="app.worker.tasks.dispatch_due_reminders")
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


@celery_app.task(name="app.worker.tasks.escalate_overdue_document_requests")
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


@celery_app.task(name="app.worker.tasks.process_document_ocr")
def process_document_ocr(document_id: str) -> dict:
    """
    Runs OCR (Tesseract, or Google Document AI if configured) against a newly
    uploaded document, classifies its type, extracts structured fields
    (PAN, GSTIN, invoice totals, names, dates), and stores extraction_confidence
    + extracted_fields on the Document row for the review UI to display.
    """
    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        if document is None:
            return {"document_id": document_id, "status": "not_found"}

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


@celery_app.task(name="app.worker.tasks.expire_subscriptions")
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
