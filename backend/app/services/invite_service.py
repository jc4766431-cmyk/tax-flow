"""
Business logic for staff/client invites (HANDOFF.md Phase 2). Creation is
firm_admin/super_admin-only and firm-scoped via the same `assert_firm_scoped`
helper every other firm-owned-resource module uses (clients, documents,
tasks, invoices) — see app/api/deps.py.

Redemption (`POST /auth/accept-invite`) lives on AuthService instead of
here, since it's a public/unauthenticated auth-flow endpoint that creates a
User, matching where register()/register_firm() already live.
"""
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import assert_firm_scoped
from app.models.invite import Invite
from app.models.user import Firm, User, UserRole
from app.repositories.invite_repository import InviteRepository
from app.schemas.invite import InviteCreate
from app.services.notification_channels import EmailSender
from app.core.config import settings

logger = logging.getLogger(__name__)

INVITE_EXPIRY_DAYS = 7


class InviteService:
    def __init__(self, db: Session):
        self.db = db
        self.invites = InviteRepository(db)

    def create_invite(self, payload: InviteCreate, current_user: User) -> Invite:
        assert_firm_scoped(current_user, payload.firm_id)

        if payload.role == UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot invite a super_admin — that role is platform-level, not firm-scoped",
            )

        firm = self.db.get(Firm, payload.firm_id)
        if firm is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Firm not found")

        invite = Invite(
            email=payload.email.lower(),
            firm_id=payload.firm_id,
            role=payload.role,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS),
        )
        invite = self.invites.create(invite)

        # Same hardcoded-frontend-domain pattern AuthService.request_password_reset
        # already uses for its own emailed link — not a new convention.
        link = f"{settings.FRONTEND_URL}/accept-invite?token={invite.token}"
        body = (
            f"You've been invited to join {firm.name} on TaxFlow as "
            f"{payload.role.value.replace('_', ' ')}. Accept your invite "
            f"(expires in {INVITE_EXPIRY_DAYS} days): {link}"
        )
        EmailSender().send_text(invite.email, body)

        return invite

    def list_invites(self, current_user: User, firm_id: uuid.UUID) -> list[Invite]:
        """Lists pending/accepted/expired invites for a firm — same
        firm-scoping rule as create_invite (super_admin may target any firm,
        firm_admin only their own)."""
        assert_firm_scoped(current_user, firm_id)
        return self.invites.list_for_firm(firm_id)
