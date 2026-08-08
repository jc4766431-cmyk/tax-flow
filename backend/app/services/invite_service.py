"""
Business logic for staff invites (HANDOFF.md Phase 2). Creation is
firm_admin/super_admin-only and firm-scoped via the same `assert_firm_scoped`
helper every other firm-owned-resource module uses (clients, documents,
tasks, invoices) — see app/api/deps.py.

create_invite() only ever mints staff-role (accountant/reviewer/firm_admin)
invites now — client-invite-first onboarding was retired in favor of
POST /clients/quick-add, so a `role: "client"` payload here 400s (see the
check below). This does NOT touch the separate, still-active
create_shadow_client_invite() below, which creates client-role Invite rows
for a different purpose (granting portal login access to an already-quick-
added client) and deliberately bypasses this method entirely.

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

        if payload.role == UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Clients are onboarded via quick-add, not invite — see POST /clients/quick-add",
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

    def create_shadow_client_invite(self, client, current_user: User) -> Invite:
        """The portal-access-upgrade path for a quick-added ("shadow user")
        client — see NEXT-PROMPT.md step 4. Deliberately NOT built on top of
        create_invite() above: that method emails the invite via
        EmailSender, but a quick-added client's User.email is always the
        unusable @taxflow.internal placeholder (see
        app/api/v1/endpoints/clients.py's quick-add endpoint) — sending
        email there would silently go nowhere. The caller (the
        invite-portal-access endpoint) sends this invite's link over
        WhatsApp instead, to client.phone.

        Reuses the Invite model as-is rather than adding a second
        lighter-weight token type: Invite.email is set to the shadow User's
        own (already-unique) placeholder address, which doubles as the
        correlation key AuthService.activate_shadow_client uses to find
        that existing User again on redemption — no new column needed on
        Invite/Client/User for this. This only works because the shadow
        user's email is already guaranteed unique; it is never a real,
        typeable address (see clients.py for why), so no live person could
        ever accidentally collide with it via POST /auth/register.
        """
        assert_firm_scoped(current_user, client.firm_id)

        invite = Invite(
            email=client.user.email,
            firm_id=client.firm_id,
            role=UserRole.CLIENT,
            token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS),
        )
        return self.invites.create(invite)

    def list_invites(self, current_user: User, firm_id: uuid.UUID) -> list[Invite]:
        """Lists pending/accepted/expired invites for a firm — same
        firm-scoping rule as create_invite (super_admin may target any firm,
        firm_admin only their own)."""
        assert_firm_scoped(current_user, firm_id)
        return self.invites.list_for_firm(firm_id)
