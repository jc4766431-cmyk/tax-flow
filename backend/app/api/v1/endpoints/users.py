import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_staff
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import StaffRead
from app.services.user_service import UserService

# Any staff role (super_admin/firm_admin/accountant/reviewer) may list staff —
# this is a read-only lookup used to populate assignee dropdowns when any
# staff member creates a filing or task, not just admins. Team-management
# actions that actually change the roster (invite/remove) stay admin-gated
# separately in invites.py — this router only ever reads.
router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(require_staff)])


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
