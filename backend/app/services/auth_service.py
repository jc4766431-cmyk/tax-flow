"""
Business logic for authentication: registration, login, token refresh.
Kept separate from the API layer so it is independently unit-testable.
"""
import uuid

import pyotp
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import logging

from app.core.security import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    PasswordResetConfirm,
    PasswordResetRequest,
    TokenPair,
    TwoFactorDisable,
    TwoFactorSetupResponse,
    TwoFactorVerify,
    UserLogin,
    UserRegister,
)
from app.services.notification_channels import EmailSender

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)

    def register(self, payload: UserRegister) -> User:
        if self.users.get_by_email(payload.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists",
            )
        user = User(
            email=payload.email.lower(),
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name,
            role=payload.role,
            firm_id=payload.firm_id,
        )
        return self.users.create(user)

    def authenticate(self, payload: UserLogin) -> TokenPair:
        user = self.users.get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated"
            )
        if user.two_factor_enabled:
            if not payload.totp_code or not self._verify_totp(user, payload.totp_code):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing or incorrect two-factor code",
                )
        return self._issue_tokens(user)

    @staticmethod
    def _verify_totp(user: User, code: str) -> bool:
        if not user.two_factor_secret:
            return False
        return pyotp.TOTP(user.two_factor_secret).verify(code, valid_window=1)

    def setup_two_factor(self, user: User) -> TwoFactorSetupResponse:
        """Generates a new secret and stores it un-enabled until confirmed
        via /auth/2fa/enable. Re-calling this before enabling replaces the
        pending secret (e.g. if the user lost the QR code)."""
        secret = pyotp.random_base32()
        user.two_factor_secret = secret
        self.users.update(user)
        uri = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name="TaxFlow")
        return TwoFactorSetupResponse(secret=secret, provisioning_uri=uri)

    def enable_two_factor(self, user: User, payload: TwoFactorVerify) -> None:
        if not self._verify_totp(user, payload.totp_code):
            raise HTTPException(status_code=400, detail="Incorrect two-factor code")
        user.two_factor_enabled = True
        self.users.update(user)

    def disable_two_factor(self, user: User, payload: TwoFactorDisable) -> None:
        if not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect password")
        if not self._verify_totp(user, payload.totp_code):
            raise HTTPException(status_code=400, detail="Incorrect two-factor code")
        user.two_factor_enabled = False
        user.two_factor_secret = None
        self.users.update(user)

    def refresh(self, refresh_token: str) -> TokenPair:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        user = self.users.get_by_id(uuid.UUID(payload["sub"]))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        return self._issue_tokens(user)

    def request_password_reset(self, payload: PasswordResetRequest) -> None:
        """Always succeeds silently even for an unknown email, so this
        endpoint can't be used to enumerate registered accounts."""
        user = self.users.get_by_email(payload.email)
        if not user:
            return
        token = create_password_reset_token(str(user.id))
        body = (
            f"Hi {user.full_name}, use this link to reset your TaxFlow "
            f"password (expires in 30 minutes): "
            f"https://app.taxflow.example/reset-password?token={token}"
        )
        EmailSender().send_text(user.email, body)

    def confirm_password_reset(self, payload: PasswordResetConfirm) -> None:
        claims = decode_token(payload.token)
        if not claims or claims.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        user = self.users.get_by_id(uuid.UUID(claims["sub"]))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token",
            )
        user.hashed_password = hash_password(payload.new_password)
        self.users.update(user)

    def _issue_tokens(self, user: User) -> TokenPair:
        access = create_access_token(
            str(user.id), role=user.role.value, firm_id=str(user.firm_id) if user.firm_id else None
        )
        refresh = create_refresh_token(str(user.id))
        return TokenPair(access_token=access, refresh_token=refresh)
