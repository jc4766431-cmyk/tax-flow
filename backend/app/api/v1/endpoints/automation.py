import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.client import Client
from app.models.document import ChecklistItem, DocumentStatus
from app.models.filing import FilingRequest
from app.models.user import User, UserRole
from app.models.workflow import Reminder
from app.schemas.automation import EscalationStatus, ReminderCreate, ReminderRead

router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/reminders", response_model=ReminderRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_staff)])
def create_reminder(payload: ReminderCreate, db: Session = Depends(get_db)):
    filing = db.get(FilingRequest, payload.filing_request_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing request not found")

    reminder = Reminder(**payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/reminders", response_model=list[ReminderRead], dependencies=[Depends(require_staff)])
def list_reminders(
    filing_request_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Reminder).where(Reminder.filing_request_id == filing_request_id)
    ).all()


@router.patch("/reminders/{reminder_id}/cancel", response_model=ReminderRead,
              dependencies=[Depends(require_staff)])
def cancel_reminder(reminder_id: uuid.UUID, db: Session = Depends(get_db)):
    reminder = db.get(Reminder, reminder_id)
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")
    reminder.cancelled = True
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/escalations", response_model=list[EscalationStatus])
def list_escalations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Derived (not stored) escalation status: one row per filing request that
    has past-due missing checklist items. `follow_ups_sent` counts non-cancelled
    reminders already sent for that filing, as a proxy for how many times the
    client has been nudged."""
    query = (
        select(Client, FilingRequest, ChecklistItem)
        .join(FilingRequest, FilingRequest.client_id == Client.id)
        .join(ChecklistItem, ChecklistItem.filing_request_id == FilingRequest.id)
        .where(
            ChecklistItem.status == DocumentStatus.MISSING,
            FilingRequest.due_date.is_not(None),
            FilingRequest.due_date < date.today(),
        )
    )
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.where(Client.firm_id == current_user.firm_id)

    rows = db.execute(query).all()

    grouped: dict[uuid.UUID, EscalationStatus] = {}
    for client, filing, item in rows:
        if filing.id not in grouped:
            follow_ups_sent = db.scalar(
                select(func.count()).select_from(Reminder).where(
                    Reminder.filing_request_id == filing.id,
                    Reminder.sent_at.is_not(None),
                    Reminder.cancelled.is_(False),
                )
            ) or 0
            grouped[filing.id] = EscalationStatus(
                client_id=client.id,
                client_name=client.company_name or str(client.id),
                filing_request_id=filing.id,
                missing_categories=[],
                due_date=filing.due_date.isoformat() if filing.due_date else None,
                days_overdue=(date.today() - filing.due_date).days,
                follow_ups_sent=follow_ups_sent,
            )
        grouped[filing.id].missing_categories.append(item.category.value)

    return list(grouped.values())
