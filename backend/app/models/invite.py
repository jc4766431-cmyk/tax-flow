"""
Staff/client invite flow (HANDOFF.md Phase 2 — self-serve firm onboarding).

An Invite is how a firm_admin (or super_admin) brings a new user into a
firm without that user ever supplying their own `role`/`firm_id` — the
same privilege-escalation concern UPDATE 27 fixed on `POST /auth/register`
applies here too, so `POST /auth/accept-invite` always takes role/firm_id
from this row, never from the acceptor's request body. See
`app/services/invite_service.py` (creation, firm-scoped) and
`AuthService.accept_invite` (redemption).

`token` is a random opaque string (not a JWT, unlike the password-reset
flow) so that revoking/expiring an invite is just a normal row update —
no need to track a signing-key epoch to invalidate it early.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.user import UserRole


class Invite(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "invites"

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), index=True
    )
    # Reuses the same UserRole enum/PG type as User.role — never SUPER_ADMIN,
    # enforced in InviteService.create_invite, not at the DB layer.
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # NULL until redeemed via POST /auth/accept-invite. An invite with a
    # non-null accepted_at is inert — accept_invite rejects re-use.
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
