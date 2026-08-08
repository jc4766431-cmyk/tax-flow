import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.client import Client
from app.models.filing import FilingRequest, FilingStageEvent
from app.models.user import User, UserRole
from app.models.workflow import AuditLog
from app.schemas.filing import (
    FilingAssignAccountant,
    FilingRequestCreate,
    FilingRequestRead,
    FilingStageUpdate,
)

router = APIRouter(prefix="/filings", tags=["filings"])


def _backfill_client_default_accountant(
    db: Session, client: Client | None, accountant_id: uuid.UUID | None
) -> None:
    """When a filing gets an accountant (on create or via assign-accountant),
    backfill Client.assigned_accountant_id only if it's currently null.
    Never overwrites an existing client-level assignment from a filing-level
    action — that would let assigning one filing to a specialist silently
    reassign the client's default accountant, which is not the intent (see
    POST/PATCH /clients/{id}/assign-accountant for the explicit, intentional
    way to change the default)."""
    if client is not None and accountant_id is not None and client.assigned_accountant_id is None:
        client.assigned_accountant_id = accountant_id
        db.add(client)


@router.post("", response_model=FilingRequestRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_staff)])
def create_filing(payload: FilingRequestCreate, db: Session = Depends(get_db)):
    filing = FilingRequest(**payload.model_dump())
    db.add(filing)
    db.commit()
    db.refresh(filing)

    db.add(FilingStageEvent(filing_request_id=filing.id, stage=filing.stage))

    client = db.get(Client, filing.client_id)
    _backfill_client_default_accountant(db, client, filing.assigned_accountant_id)

    db.commit()
    db.refresh(filing)
    return filing


@router.patch("/{filing_id}/assign-accountant", response_model=FilingRequestRead,
              dependencies=[Depends(require_staff)])
def assign_filing_accountant(
    filing_id: uuid.UUID,
    payload: FilingAssignAccountant,
    db: Session = Depends(get_db),
):
    """Sets/changes this specific filing's accountant. Backfills the
    client's default accountant only if it's still unset (see
    _backfill_client_default_accountant) — never overwrites an existing
    client-level assignment."""
    filing = db.get(FilingRequest, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing request not found")

    filing.assigned_accountant_id = payload.assigned_accountant_id
    db.add(filing)

    client = db.get(Client, filing.client_id)
    _backfill_client_default_accountant(db, client, filing.assigned_accountant_id)

    db.commit()
    db.refresh(filing)
    return filing


@router.get("/{filing_id}", response_model=FilingRequestRead)
def get_filing(
    filing_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filing = db.get(FilingRequest, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing request not found")

    if current_user.role == UserRole.CLIENT and filing.client.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return filing


@router.patch("/{filing_id}/stage", response_model=FilingRequestRead,
              dependencies=[Depends(require_staff)])
def update_stage(
    filing_id: uuid.UUID,
    payload: FilingStageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a filing to a new workflow stage; records timeline event + audit log entry."""
    filing = db.get(FilingRequest, filing_id)
    if not filing:
        raise HTTPException(status_code=404, detail="Filing request not found")

    filing.stage = payload.stage
    db.add(filing)

    db.add(FilingStageEvent(
        filing_request_id=filing.id,
        stage=payload.stage,
        responsible_user_id=current_user.id,
        notes=payload.notes,
    ))
    db.add(AuditLog(
        actor_user_id=current_user.id,
        action="filing.stage_changed",
        resource_type="filing_request",
        resource_id=str(filing.id),
        metadata_json={"new_stage": payload.stage.value, "notes": payload.notes},
    ))
    db.commit()
    db.refresh(filing)
    return filing


@router.get("", response_model=list[FilingRequestRead], dependencies=[Depends(require_staff)])
def list_filings(db: Session = Depends(get_db)):
    return db.scalars(select(FilingRequest)).all()
