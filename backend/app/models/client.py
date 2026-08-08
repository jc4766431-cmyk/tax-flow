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

    # Contact number for phone-first ("quick-add") onboarding — see
    # NEXT-PROMPT.md's phone-first client onboarding spec. Deliberately
    # separate from User.phone: this is "do we have a contact number for
    # this client," User.phone (still unused for CLIENT-role users today)
    # would be "has this client verified a phone through the portal" if it
    # were ever used that way — two different facts, not interchangeable.
    # Stored normalized (last-10-digits, via WhatsAppService.normalize_phone)
    # so WhatsAppService.match_client can compare it directly.
    phone: Mapped[str | None] = mapped_column(String(30), index=True)

    assigned_accountant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_accountant: Mapped["User | None"] = relationship(
        back_populates="assigned_clients", foreign_keys=[assigned_accountant_id]
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="client")
    filing_requests: Mapped[list["FilingRequest"]] = relationship(back_populates="client")

    @property
    def has_portal_access(self) -> bool:
        """True once this client's backing User has a real, usable login —
        i.e. the shadow-user "quick add" flow (see NEXT-PROMPT.md) has been
        upgraded via POST /clients/{id}/invite-portal-access +
        POST /auth/accept-client-invite. False for a brand-new shadow user
        (is_active=False, unusable password) and for the brief window before
        `user` is loaded — treated as "no access" rather than raising, since
        this is a display-only convenience field, not a security check."""
        return bool(self.user and self.user.is_active)
