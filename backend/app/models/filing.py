"""
Filing request lifecycle — the core workflow object clients and accountants track.
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class FilingStage(str, enum.Enum):
    REQUESTED = "requested"
    DOCUMENTS_UPLOADED = "documents_uploaded"
    UNDER_REVIEW = "under_review"
    APPROVAL_REQUIRED = "approval_required"
    FILED = "filed"
    COMPLETED = "completed"


class FilingType(str, enum.Enum):
    INCOME_TAX_RETURN = "income_tax_return"
    GST_RETURN = "gst_return"
    TDS_RETURN = "tds_return"
    AUDIT = "audit"
    OTHER = "other"


class FilingRequest(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "filing_requests"

    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE")
    )
    client: Mapped["Client"] = relationship(back_populates="filing_requests")

    filing_type: Mapped[FilingType] = mapped_column(Enum(FilingType), nullable=False)
    stage: Mapped[FilingStage] = mapped_column(Enum(FilingStage), default=FilingStage.REQUESTED)

    assigned_accountant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    period_label: Mapped[str | None] = mapped_column(String(50))  # e.g. "FY 2025-26"
    due_date: Mapped[date | None] = mapped_column(Date)
    filed_date: Mapped[date | None] = mapped_column(Date)

    notes: Mapped[str | None] = mapped_column(String(2000))

    stage_history: Mapped[list["FilingStageEvent"]] = relationship(
        back_populates="filing_request", order_by="FilingStageEvent.created_at"
    )


class FilingStageEvent(Base, UUIDMixin, TimestampMixin):
    """Audit trail of stage transitions, powering the client-facing timeline UI."""
    __tablename__ = "filing_stage_events"

    filing_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("filing_requests.id", ondelete="CASCADE")
    )
    filing_request: Mapped["FilingRequest"] = relationship(back_populates="stage_history")

    stage: Mapped[FilingStage] = mapped_column(Enum(FilingStage), nullable=False)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(String(1000))
