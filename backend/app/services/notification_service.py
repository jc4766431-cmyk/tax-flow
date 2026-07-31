import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationPage


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationRepository(db)

    def list_for_current_user(self, current_user: User, page: int, page_size: int) -> NotificationPage:
        items, total = self.notifications.list_for_user(current_user.id, page, page_size)
        return NotificationPage(items=items, total=total, page=page, page_size=page_size)

    def mark_read(self, notification_id: uuid.UUID, current_user: User):
        notification = self.notifications.get_by_id(notification_id)
        if notification is None or notification.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        return self.notifications.mark_read(notification)

    def mark_all_read(self, current_user: User) -> None:
        self.notifications.mark_all_read(current_user.id)
