from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    FirmRegister,
    FirmRegisterRead,
    InviteAcceptRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    ShadowClientActivateRequest,
    TokenPair,
    TwoFactorDisable,
    TwoFactorSetupResponse,
    TwoFactorVerify,
    UserLogin,
    UserRead,
    UserRegister,
)
from app.schemas.firm import FirmRead
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    return AuthService(db).register(payload)


@router.post("/register-firm", response_model=FirmRegisterRead, status_code=status.HTTP_201_CREATED)
def register_firm(payload: FirmRegister, db: Session = Depends(get_db)):
    """Public, unauthenticated self-serve firm signup — creates a new Firm
    and its first firm_admin User in one transaction (AuthService.register_firm).
    This is the flow the landing page's "Get Started" CTA now points at for
    the firm audience it's aimed at; /register remains the separate
    client self-signup path."""
    firm, admin = AuthService(db).register_firm(payload)
    return FirmRegisterRead(firm=FirmRead.model_validate(firm), admin=UserRead.model_validate(admin))


@router.post("/accept-invite", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def accept_invite(payload: InviteAcceptRequest, db: Session = Depends(get_db)):
    """Public, unauthenticated. Redeems a pending Invite (see POST /invites)
    into a real User, with role/firm_id taken from the invite row, never
    from this payload."""
    return AuthService(db).accept_invite(payload)


@router.post("/accept-client-invite", response_model=UserRead, status_code=status.HTTP_200_OK)
def accept_client_invite(payload: ShadowClientActivateRequest, db: Session = Depends(get_db)):
    """Public, unauthenticated. Redeems the invite created by
    POST /clients/{id}/invite-portal-access — sets a real password (and
    optionally a real email) on an existing quick-added client's shadow
    User and flips is_active=True. After this, POST /auth/login behaves
    exactly like any other client login (see AuthService.activate_shadow_client's
    docstring for why this is a distinct method from accept_invite)."""
    return AuthService(db).activate_shadow_client(payload)


@router.post("/login", response_model=TokenPair)
@limiter.limit("5/minute")
def login(request: Request, payload: UserLogin, db: Session = Depends(get_db)):
    return AuthService(db).authenticate(payload)


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    return AuthService(db).refresh(payload.refresh_token)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    AuthService(db).request_password_reset(payload)
    return {"detail": "If that email is registered, a reset link has been sent"}


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    AuthService(db).confirm_password_reset(payload)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return AuthService(db).setup_two_factor(current_user)


@router.post("/2fa/enable", status_code=status.HTTP_204_NO_CONTENT)
def enable_two_factor(
    payload: TwoFactorVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    AuthService(db).enable_two_factor(current_user, payload)


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
def disable_two_factor(
    payload: TwoFactorDisable,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    AuthService(db).disable_two_factor(current_user, payload)
