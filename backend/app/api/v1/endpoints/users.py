import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import StaffRead
from app.services.user_service import UserService

# firm_admin/super_admin only — same router-level require_admin gate as
# invites.py, since staff listing is admin/team-management surface, not
# something accountant/reviewer/client roles need.
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[StaffRead])
def list_users(
    firm_id: uuid.UUID = Query(..., description="firm_admin must pass their own firm_id; super_admin may pass any"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists a firm's staff (super_admin/firm_admin/accountant/reviewer),
    excluding client-role users — pairs with GET /invites on the admin Team
    page to show current roster alongside pending invites."""
    return UserService(db).list_staff(current_user, firm_id)


@router.get("/pending-clients", response_model=list[StaffRead])
def list_pending_client_profiles(
    firm_id: uuid.UUID = Query(..., description="firm_admin must pass their own firm_id; super_admin may pass any"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """CLIENT-role users who accepted an invite but don't have a Client row
    yet — feeds the admin Clients page's 'Add client' flow so staff can turn
    an accepted invite into a full client profile via POST /clients, without
    needing to know the invited user's id."""
    return UserService(db).list_pending_client_profiles(current_user, firm_id)
