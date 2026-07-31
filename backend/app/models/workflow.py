"""
Task management, notifications, messaging, reminders, and audit logging.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class TaskStatus(str, enum.Enum):
    NEW = "new"
    WAITING_FOR_DOCUMENTS = "waiting_for_documents"
    REVIEW = "review"
    APPROVAL = "approval"
    FILED = "filed"
    COMPLETED = "completed"


class Task(Base, UUIDMixin, TimestampMixin):
    """Kanban card on the accountant workflow board."""
    __tablename__ = "tasks"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.NEW)

    # Denormalized onto Task rather than derived by joining through client_id,
    # because client_id is nullable (a task doesn't have to be tied to a
    # client) and assigned_to_id can be reassigned or unset later — neither
    # is a reliable join path for firm-scoping on every row. Set once at
    # creation by task_service.create_task and never changed afterwards.
    # Nullable at the DB level because there's no live DB in this pass to
    # backfill any existing rows (see HANDOFF.md UPDATE 6) — a NULL value is
    # treated as "pre-fix row, only super_admin can touch it" until backfilled,
    # not as "unscoped, anyone can touch it".
    firm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), index=True
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    filing_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filing_requests.id", ondelete="CASCADE")
    )
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class NotificationType(str, enum.Enum):
    DEADLINE_REMINDER = "deadline_reminder"
    MISSING_DOCUMENT = "missing_document"
    APPROVAL_REQUEST = "approval_request"
    FILING_COMPLETED = "filing_completed"
    NEW_MESSAGE = "new_message"


class Notification(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(String(1000))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    link_url: Mapped[str | None] = mapped_column(String(500))


class Message(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "messages"

    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(String(5000))
    attachment_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReminderChannel(str, enum.Enum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class Reminder(Base, UUIDMixin, TimestampMixin):
    """Configured automated deadline reminder (e.g. 7 days before due date, via email)."""
    __tablename__ = "reminders"

    filing_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filing_requests.id", ondelete="CASCADE")
    )
    days_before_deadline: Mapped[int] = mapped_column()
    channel: Mapped[ReminderChannel] = mapped_column(Enum(ReminderChannel), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base, UUIDMixin, TimestampMixin):
    """Immutable record of security-relevant and business-relevant actions."""
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(255))  # e.g. "document.approved"
    resource_type: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))
