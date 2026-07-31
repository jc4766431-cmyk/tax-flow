import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.workflow import Message


class MessageRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, message_id: uuid.UUID) -> Message | None:
        return self.db.get(Message, message_id)

    def list_thread(self, client_id: uuid.UUID, page: int, page_size: int) -> tuple[list[Message], int]:
        base = select(Message).where(Message.client_id == client_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery()))
        stmt = (
            base.order_by(Message.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt).all()), total or 0

    def create(self, message: Message) -> Message:
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def mark_read(self, message: Message) -> Message:
        from datetime import datetime, timezone

        message.read_at = datetime.now(timezone.utc)
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
