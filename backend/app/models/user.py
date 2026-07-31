"""
User, Firm, and role-based access control models.
"""
import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    FIRM_ADMIN = "firm_admin"
    ACCOUNTANT = "accountant"
    REVIEWER = "reviewer"
    CLIENT = "client"


class Firm(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "firms"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255))
    tax_registration_number: Mapped[str | None] = mapped_column(String(100))
    address: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list["User"]] = relationship(back_populates="firm")


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.CLIENT)

    firm_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="SET NULL")
    )
    firm: Mapped[Firm | None] = relationship(back_populates="users")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    two_factor_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Base32 TOTP secret (pyotp). Set on /auth/2fa/setup, kept even while
    # two_factor_enabled is still False (pending verification), cleared on
    # disable. Never exposed via UserRead.
    two_factor_secret: Mapped[str | None] = mapped_column(String(32))

    # Only set on CLIENT-role users; links to their client profile
    client_profile: Mapped["Client | None"] = relationship(
        back_populates="user", uselist=False, foreign_keys="Client.user_id"
    )

    # Only set on ACCOUNTANT/REVIEWER-role users
    assigned_clients: Mapped[list["Client"]] = relationship(
        back_populates="assigned_accountant",
        foreign_keys="Client.assigned_accountant_id",
    )
