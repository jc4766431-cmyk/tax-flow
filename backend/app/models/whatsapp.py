"""
WhatsApp-first client channel — inbound message log.

This is deliberately a log/audit table, not a chat-history feature (that's
`Message`/§2d's job for staff-client threads). Its job is:
  1. Idempotency — Meta retries webhook deliveries; `wa_message_id` is unique
     so re-processing the same delivery is a no-op, not a duplicate document.
  2. Observability — every inbound WhatsApp event has a row here showing what
     was received, whether it matched a client, and what (if anything) it
     produced, so failures are debuggable without re-reading raw webhook logs.

See app/services/whatsapp_service.py for the processing pipeline and
NEXT-PROMPT.md for the design constraints this was built against.
"""
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class WhatsAppMessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class WhatsAppProcessingStatus(str, enum.Enum):
    RECEIVED = "received"
    UNMATCHED = "unmatched"          # no Client found for the sending phone number
    ACKNOWLEDGED = "acknowledged"     # matched a client, text message, no document produced
    DOCUMENT_CREATED = "document_created"
    ERROR = "error"


class WhatsAppInboundMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "whatsapp_inbound_messages"

    wa_message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    from_phone: Mapped[str] = mapped_column(String(30), nullable=False)

    message_type: Mapped[WhatsAppMessageType] = mapped_column(
        Enum(WhatsAppMessageType), default=WhatsAppMessageType.UNKNOWN
    )
    processing_status: Mapped[WhatsAppProcessingStatus] = mapped_column(
        Enum(WhatsAppProcessingStatus), default=WhatsAppProcessingStatus.RECEIVED
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="SET NULL")
    )
    created_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )

    raw_payload: Mapped[dict] = mapped_column(JSONB)
    error_detail: Mapped[str | None] = mapped_column(String(1000))
