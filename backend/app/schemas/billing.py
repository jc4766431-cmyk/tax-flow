import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.billing import BillingPeriod, PlanTier, SubscriptionStatus


class PlanCreate(BaseModel):
    tier: PlanTier
    name: str
    description: str | None = None
    price_per_seat_inr: float | None = None
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    min_seats: int = 1
    max_seats: int | None = None
    max_clients: int | None = None
    is_active: bool = True


class PlanUpdate(BaseModel):
    """Partial edit — e.g. adjusting price or deactivating a tier without
    retiring the historical rows that reference it."""
    name: str | None = None
    description: str | None = None
    price_per_seat_inr: float | None = None
    billing_period: BillingPeriod | None = None
    min_seats: int | None = None
    max_seats: int | None = None
    max_clients: int | None = None
    is_active: bool | None = None


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tier: PlanTier
    name: str
    description: str | None
    price_per_seat_inr: float | None
    billing_period: BillingPeriod
    min_seats: int
    max_seats: int | None
    max_clients: int | None
    is_active: bool


class SubscriptionCreate(BaseModel):
    """Starts (or restarts) a firm's subscription. firm_id is resolved from
    the requesting firm_admin's own firm_id at the service layer for
    non-super-admins — see billing_service.py — a super_admin may pass an
    explicit firm_id to start a subscription on a firm's behalf."""
    plan_id: uuid.UUID
    seats: int = 1
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    firm_id: uuid.UUID | None = None


class SubscriptionUpgrade(BaseModel):
    """Change plan and/or seat count on the firm's current subscription.
    Both fields optional so a caller can send just the one that changed."""
    plan_id: uuid.UUID | None = None
    seats: int | None = None
    billing_period: BillingPeriod | None = None


class SubscriptionCancel(BaseModel):
    # Default True: cancel at the end of the already-paid-for period rather
    # than immediately revoking access the firm has already paid for.
    at_period_end: bool = True


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    firm_id: uuid.UUID
    plan_id: uuid.UUID
    plan: PlanRead
    seats: int
    billing_period: BillingPeriod
    status: SubscriptionStatus
    current_period_start: date
    current_period_end: date
    cancel_at_period_end: bool
    cancelled_at: date | None
    payment_gateway_ref: str | None
