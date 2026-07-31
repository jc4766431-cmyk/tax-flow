"""
Shared FastAPI dependencies: DB session, current-user resolution, and
role-based access control guards.
"""
import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.get(User, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def assert_firm_scoped(current_user: User, target_firm_id: uuid.UUID | None) -> None:
    """Enforces firm-scoping for staff users acting on a firm-owned resource
    (a Client, or anything hanging off a Client such as a Document).

    - SUPER_ADMIN is platform-level and bypasses this check by design (can act
      across firms, e.g. for support/ops purposes).
    - FIRM_ADMIN/ACCOUNTANT/REVIEWER may only act on resources belonging to
      their own firm_id.
    - CLIENT-role users are NOT scoped by this helper — they are scoped to
      their own client_id via a separate check (see document_service.py /
      clients.py), since a client has no firm_id of their own to compare.

    This closes the firm-scoping gap flagged in HANDOFF.md §2/§0c/§0d, where
    a non-admin accountant could previously view/act on any firm's clients
    and documents, not just their own firm's.
    """
    if current_user.role == UserRole.SUPER_ADMIN:
        return
    if current_user.firm_id is None or current_user.firm_id != target_firm_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to a different firm",
        )


def require_roles(*allowed_roles: UserRole) -> Callable:
    """
    Dependency factory implementing RBAC:

        @router.get("/admin-only", dependencies=[Depends(require_roles(UserRole.FIRM_ADMIN))])
    """

    def _guard(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _guard


# Common role groupings used across endpoints
require_staff = require_roles(
    UserRole.SUPER_ADMIN, UserRole.FIRM_ADMIN, UserRole.ACCOUNTANT, UserRole.REVIEWER
)
require_admin = require_roles(UserRole.SUPER_ADMIN, UserRole.FIRM_ADMIN)
