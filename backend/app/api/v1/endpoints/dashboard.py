from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.client import Client
from app.models.document import Document, DocumentStatus
from app.models.filing import FilingRequest, FilingStage
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/firm-overview", dependencies=[Depends(require_staff)])
def firm_overview(db: Session = Depends(get_db)):
    """Powers the accountant dashboard's top-level stat cards."""
    active_clients = db.scalar(select(func.count()).select_from(Client)) or 0

    pending_filings = db.scalar(
        select(func.count()).select_from(FilingRequest).where(
            FilingRequest.stage.notin_([FilingStage.FILED, FilingStage.COMPLETED])
        )
    ) or 0

    overdue_tasks = db.scalar(
        select(func.count()).select_from(FilingRequest).where(
            FilingRequest.due_date < date.today(),
            FilingRequest.stage.notin_([FilingStage.FILED, FilingStage.COMPLETED]),
        )
    ) or 0

    docs_awaiting_review = db.scalar(
        select(func.count()).select_from(Document).where(
            Document.status == DocumentStatus.UNDER_REVIEW
        )
    ) or 0

    upcoming_deadline_cutoff = date.today() + timedelta(days=14)
    upcoming_deadlines = db.scalar(
        select(func.count()).select_from(FilingRequest).where(
            FilingRequest.due_date.between(date.today(), upcoming_deadline_cutoff)
        )
    ) or 0

    return {
        "active_clients": active_clients,
        "pending_filings": pending_filings,
        "overdue_tasks": overdue_tasks,
        "documents_awaiting_review": docs_awaiting_review,
        "upcoming_deadlines_14d": upcoming_deadlines,
    }


@router.get("/client-overview")
def client_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Powers the client portal dashboard widgets for the logged-in client."""
    client = db.scalar(select(Client).where(Client.user_id == current_user.id))
    if not client:
        return {
            "upcoming_deadlines": [],
            "filing_status": [],
            "pending_uploads": 0,
        }

    filings = db.scalars(
        select(FilingRequest).where(FilingRequest.client_id == client.id)
    ).all()

    missing_docs = db.scalar(
        select(func.count()).select_from(Document).where(
            Document.client_id == client.id, Document.status == DocumentStatus.MISSING
        )
    ) or 0

    return {
        "client_id": str(client.id),
        "assigned_accountant_id": str(client.assigned_accountant_id) if client.assigned_accountant_id else None,
        "filing_status": [
            {"id": str(f.id), "type": f.filing_type.value, "stage": f.stage.value, "due_date": f.due_date}
            for f in filings
        ],
        "pending_uploads": missing_docs,
    }
