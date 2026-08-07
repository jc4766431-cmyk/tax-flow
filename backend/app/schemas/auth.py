"""
Request/response models for authentication endpoints.
"""
import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole
from app.schemas.firm import FirmRead


class UserRegister(BaseModel):
    """
    Public, unauthenticated self-registration. Deliberately does NOT accept
    `role` or `firm_id` from the client — every self-registered account is
    always a CLIENT with no firm attached (see AuthService.register).

    Staff accounts (firm_admin/accountant/reviewer) and firm-scoped clients
    are created exclusively through the firm-signup and invite-accept flows
    (`POST /auth/register-firm`, `POST /auth/accept-invite`), which set
    role/firm_id server-side, never from unauthenticated client input.
    Accepting `role`/`firm_id` here used to let any anonymous caller
    self-register as `super_admin` or as `firm_admin` of an arbitrary
    firm_id — a privilege-escalation hole that made the firm-scoping RBAC
    checks in app/api/deps.py meaningless, since an attacker could just
    mint themselves a super_admin token instead of working around the
    scoping. Found and fixed during the Phase 1 firm-scoping
    live-verification pass — see HANDOFF.md.
    """

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class TwoFactorSetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class TwoFactorVerify(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6)


class TwoFactorDisable(BaseModel):
    password: str
    totp_code: str = Field(min_length=6, max_length=6)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
    firm_id: uuid.UUID | None
    is_active: bool
    is_email_verified: bool
    two_factor_enabled: bool


class FirmRegister(BaseModel):
    """
    Public, unauthenticated self-serve firm signup —
    `POST /auth/register-firm`, referenced by UserRegister's docstring
    above. Creates a new Firm and its first firm_admin User in one
    transaction (see AuthService.register_firm). This, along with
    `POST /auth/accept-invite`, is now the only way to create a
    non-CLIENT account, since UserRegister no longer accepts role/firm_id
    (see that docstring for why).
    """

    firm_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class FirmRegisterRead(BaseModel):
    # UserRead is defined above this class (not a forward reference) so
    # this doesn't need a model_rebuild() call to resolve it.
    firm: FirmRead
    admin: UserRead


class InviteAcceptRequest(BaseModel):
    """Public, unauthenticated. `token` identifies a pending Invite row
    (app/models/invite.py), which supplies the role/firm_id/email for the
    new account server-side — never accepted from this payload, same
    reasoning as UserRegister no longer accepting them directly."""

    token: str
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
