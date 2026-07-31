"""
Subscription billing — the firm's *own* TaxFlow account (per-accountant/
month, INR), per STRATEGY_REVIEW.md Phase 7 and NEXT-PROMPT.md's "Must build
before launch" item 3.

Deliberately a distinct module from the firm's-own-client invoicing
mentioned in HANDOFF.md §5 (billing the firm charges *its* clients) — don't
conflate the two. This module answers "how much does this firm pay
TaxFlow," not "how much does this firm's client owe them."

No payment gateway is wired up here and none is guessed at — see the TODO
in billing_service.py for exactly where a real gateway (Razorpay is the
obvious India-first choice per Phase 6/7, but that's a decision to confirm,
not assume) would plug in.
"""
import enum
import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.base import TimestampMixin, UUIDMixin


class PlanTier(str, enum.Enum):
    FREE = "free"
    SOLO = "solo"
    TEAM = "team"
    FIRM = "firm"
    ENTERPRISE = "enterprise"


class BillingPeriod(str, enum.Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class SubscriptionStatus(str, enum.Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"


class Plan(Base, UUIDMixin, TimestampMixin):
    """A sellable pricing tier, per STRATEGY_REVIEW.md Phase 7:
    Solo (flat, or a free acquisition tier), Team, Firm (+ compliance-risk
    add-on, priced separately, not modeled here yet — see HANDOFF §5), and
    Enterprise (custom, price_per_seat_inr left null to mean "contact us").
    """
    __tablename__ = "plans"

    tier: Mapped[PlanTier] = mapped_column(Enum(PlanTier), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))

    # Null only for ENTERPRISE ("custom" pricing, negotiated per firm).
    price_per_seat_inr: Mapped[float | None] = mapped_column(Numeric(10, 2))
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod), default=BillingPeriod.MONTHLY
    )

    # Null = unlimited seats (Enterprise). 0 is not meaningful and not used.
    min_seats: Mapped[int] = mapped_column(Integer, default=1)
    max_seats: Mapped[int | None] = mapped_column(Integer)

    # Free-tier hard limits, per Phase 7 ("free tier with hard limits — 5
    # clients, no automation"). Null means "not applicable / no cap" for
    # paid tiers, not "actually unlimited" — paid tiers simply don't use
    # this field to gate anything today.
    max_clients: Mapped[int | None] = mapped_column(Integer)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base, UUIDMixin, TimestampMixin):
    """A firm's subscription to a Plan. One firm may have a history of rows
    here (e.g. a cancelled Solo sub followed by a new Team sub) — the
    "current" one is whichever has the latest current_period_end among
    non-cancelled rows; see billing_service.get_active_subscription rather
    than assuming the most-recently-created row is authoritative."""
    __tablename__ = "subscriptions"

    firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("firms.id", ondelete="CASCADE"), index=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT")
    )
    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")

    seats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    billing_period: Mapped[BillingPeriod] = mapped_column(
        Enum(BillingPeriod), default=BillingPeriod.MONTHLY
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus), default=SubscriptionStatus.TRIALING
    )

    current_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    current_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelled_at: Mapped[date | None] = mapped_column(Date)

    # Where a real gateway's subscription/customer reference would be stored
    # once one is wired up (e.g. a Razorpay subscription_id) — null today,
    # by design, not a placeholder bug. See billing_service.py's TODO.
    payment_gateway_ref: Mapped[str | None] = mapped_column(String(255))
