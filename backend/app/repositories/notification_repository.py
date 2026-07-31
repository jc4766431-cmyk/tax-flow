import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.workflow import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, notification_id: uuid.UUID) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def list_for_user(self, user_id: uuid.UUID, page: int, page_size: int) -> tuple[list[Notification], int]:
        # Unread-first, then most recent.
        base = select(Notification).where(Notification.user_id == user_id)
        total = self.db.scalar(select(func.count()).select_from(base.subquery()))
        stmt = (
            base.order_by(Notification.is_read.asc(), Notification.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(self.db.scalars(stmt).all()), total or 0

    def mark_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read(self, user_id: uuid.UUID) -> None:
        self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        self.db.commit()

    def create(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification
