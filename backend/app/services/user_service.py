"""
Business logic for user/staff management. list_staff mirrors
InviteService.list_invites' firm-scoping: super_admin may target any firm,
all other staff roles (firm_admin/accountant/reviewer) only their own,
via the shared assert_firm_scoped helper.
"""
import uuid

from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def list_staff(self, current_user: User, firm_id: uuid.UUID) -> list[User]:
        """Lists a firm's staff (super_admin/firm_admin/accountant/reviewer),
        excluding client-role users, for the admin Team page."""
        assert_firm_scoped(current_user, firm_id)
        return self.users.list_staff_for_firm(firm_id)
