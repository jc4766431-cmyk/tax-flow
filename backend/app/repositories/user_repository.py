"""
Repository pattern: isolates SQLAlchemy queries from business logic (services).
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def list_staff_for_firm(self, firm_id: uuid.UUID) -> list[User]:
        """Staff (non-client) users for a firm, for the admin Team page's
        'current staff' roster — excludes CLIENT-role users the same way
        InviteRepository.list_for_firm is already scoped to one firm."""
        stmt = (
            select(User)
            .where(User.firm_id == firm_id, User.role != UserRole.CLIENT)
            .order_by(User.full_name)
        )
        return list(self.db.scalars(stmt).all())

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self.db.scalar(stmt)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
