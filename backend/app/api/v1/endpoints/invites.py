from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.invite import InviteCreate, InviteRead
from app.services.invite_service import InviteService

# firm_admin/super_admin action, per HANDOFF's Phase 2 spec — mirrors
# invoices.py's router-level require_admin gate.
router = APIRouter(prefix="/invites", tags=["invites"], dependencies=[Depends(require_admin)])


@router.post("", response_model=InviteRead, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return InviteService(db).create_invite(payload, current_user)
