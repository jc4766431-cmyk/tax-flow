"""
Platform-level Firm management. Closes the gap flagged repeatedly in
HANDOFF.md (§0d/§0g/etc.): no endpoint previously existed to create a
Firm, forcing every prior pass to insert one directly via a DB shell for
testing. Super-admin only, since firm creation is a platform-level
(cross-firm) action, same rule already used for /billing/plans writes.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.user import Firm, UserRole
from app.schemas.firm import FirmCreate, FirmRead

router = APIRouter(prefix="/firms", tags=["firms"])

require_super_admin = require_roles(UserRole.SUPER_ADMIN)


@router.post("", response_model=FirmRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_super_admin)])
def create_firm(payload: FirmCreate, db: Session = Depends(get_db)):
    firm = Firm(**payload.model_dump())
    db.add(firm)
    db.commit()
    db.refresh(firm)
    return firm


@router.get("", response_model=list[FirmRead], dependencies=[Depends(require_super_admin)])
def list_firms(db: Session = Depends(get_db)):
    return db.query(Firm).order_by(Firm.name).all()


@router.get("/{firm_id}", response_model=FirmRead, dependencies=[Depends(require_super_admin)])
def get_firm(firm_id: uuid.UUID, db: Session = Depends(get_db)):
    firm = db.get(Firm, firm_id)
    if firm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")
    return firm
