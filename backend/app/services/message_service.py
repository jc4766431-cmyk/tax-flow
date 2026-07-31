import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.user import User, UserRole
from app.models.workflow import Message, Notification, NotificationType
from app.repositories.message_repository import MessageRepository
from app.schemas.message import MessageCreate, MessagePage


class MessageService:
    def __init__(self, db: Session):
        self.db = db
        self.messages = MessageRepository(db)

    def _assert_thread_access(self, client: Client, current_user: User) -> None:
        """Only the client themself, their assigned accountant, and firm
        admins/super_admin may read or write a given client's message thread."""
        if current_user.role == UserRole.SUPER_ADMIN:
            return
        if current_user.role == UserRole.CLIENT:
            if current_user.client_profile and current_user.client_profile.id == client.id:
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        if current_user.role == UserRole.FIRM_ADMIN:
            if current_user.firm_id == client.firm_id:
                return
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        # Accountant/reviewer: must be the client's assigned accountant.
        if current_user.id == client.assigned_accountant_id:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    def _get_client(self, client_id: uuid.UUID) -> Client:
        client = self.db.get(Client, client_id)
        if client is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    def get_thread(self, client_id: uuid.UUID, current_user: User, page: int, page_size: int) -> MessagePage:
        client = self._get_client(client_id)
        self._assert_thread_access(client, current_user)
        items, total = self.messages.list_thread(client_id, page, page_size)
        return MessagePage(items=items, total=total, page=page, page_size=page_size)

    def send_message(self, payload: MessageCreate, current_user: User) -> Message:
        client = self._get_client(payload.client_id)
        self._assert_thread_access(client, current_user)
        message = Message(
            sender_id=current_user.id,
            recipient_id=payload.recipient_id,
            client_id=payload.client_id,
            body=payload.body,
            attachment_document_id=payload.attachment_document_id,
        )
        message = self.messages.create(message)
        # Notify the recipient a new message has arrived, per §2c's rule that
        # notifications are created by other services, not a public endpoint.
        self.db.add(
            Notification(
                user_id=payload.recipient_id,
                type=NotificationType.NEW_MESSAGE,
                title="New message",
                body=message.body[:200],
            )
        )
        self.db.commit()
        return message

    def mark_read(self, message_id: uuid.UUID, current_user: User) -> Message:
        message = self.messages.get_by_id(message_id)
        if message is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
        if message.recipient_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return self.messages.mark_read(message)
