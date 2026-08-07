from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invite import Invite


class InviteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_token(self, token: str) -> Invite | None:
        return self.db.scalar(select(Invite).where(Invite.token == token))

    def create(self, invite: Invite) -> Invite:
        self.db.add(invite)
        self.db.commit()
        self.db.refresh(invite)
        return invite

    def save(self, invite: Invite) -> Invite:
        self.db.commit()
        self.db.refresh(invite)
        return invite
