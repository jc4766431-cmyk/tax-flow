"""
Client profile model — the taxpayer/company being served by the firm.
"""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    user: Mapped["User"] = relationship(
        back_populates="client_profile", foreign_keys=[user_id]
    )

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE")
    )

    company_name: Mapped[str | None] = mapped_column(String(255))
    pan_number: Mapped[str | None] = mapped_column(String(20))
    gstin: Mapped[str | None] = mapped_column(String(20))

    assigned_accountant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_accountant: Mapped["User | None"] = relationship(
        back_populates="assigned_clients", foreign_keys=[assigned_accountant_id]
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="client")
    filing_requests: Mapped[list["FilingRequest"]] = relationship(back_populates="client")
