"""
Business logic for subscription billing (the firm's own TaxFlow account —
see models/billing.py's module docstring for why this is a distinct module
from client invoicing).

No payment gateway is wired up. Every method that would, in a real deployment,
trigger a charge or a gateway-side subscription change is marked with a
TODO(payment-gateway) comment at the exact call site — Razorpay is the
obvious India-first choice per STRATEGY_REVIEW.md Phase 6/7, but that's a
product decision to confirm with the user, not assume here. Until a gateway
is wired up, subscriptions are created directly in ACTIVE/TRIALING status
and period rollover is not automated (no Celery beat task exists yet to
expire a subscription whose current_period_end has passed — see HANDOFF.md
§2e's worker-task stubs for the pattern to extend when that's built).
"""
import calendar
import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.billing import BillingPeriod, Plan, PlanTier, Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.repositories.billing_repository import PlanRepository, SubscriptionRepository
from app.schemas.billing import (
    PlanCreate,
    PlanUpdate,
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionUpgrade,
)


def _add_one_month(d: date) -> date:
    """Adds exactly one calendar month, clamping the day to the shorter
    month's length (e.g. Jan 31 -> Feb 28/29) rather than overflowing into
    the next month — the behavior a billing period boundary needs."""
    month = d.month + 1
    year = d.year + (month - 1) // 12
    month = (month - 1) % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _period_end(start: date, billing_period: BillingPeriod) -> date:
    if billing_period == BillingPeriod.ANNUAL:
        return start + timedelta(days=365)
    return _add_one_month(start)


class PlanService:
    def __init__(self, db: Session):
        self.db = db
        self.plans = PlanRepository(db)

    def list_plans(self, *, active_only: bool = True) -> list[Plan]:
        return self.plans.list_plans(active_only=active_only)

    def get_plan(self, plan_id: uuid.UUID) -> Plan:
        plan = self.plans.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        return plan

    def create_plan(self, payload: PlanCreate) -> Plan:
        if self.plans.get_by_tier(payload.tier):
            raise HTTPException(
                status_code=400, detail=f"A plan for tier {payload.tier.value!r} already exists"
            )
        plan = Plan(**payload.model_dump())
        return self.plans.create(plan)

    def update_plan(self, plan_id: uuid.UUID, payload: PlanUpdate) -> Plan:
        plan = self.get_plan(plan_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(plan, field, value)
        return self.plans.update(plan)


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionRepository(db)
        self.plans = PlanRepository(db)

    # --- Access control helpers ---------------------------------------
    # Same firm-scoping pattern as task_service.py: non-super-admin staff are
    # confined to their own firm. Billing is admin-only at the router level
    # (require_admin), so there's no client-role or non-admin-staff branch.

    def _resolve_firm_id(self, current_user: User, requested_firm_id: uuid.UUID | None) -> uuid.UUID:
        if current_user.role == UserRole.SUPER_ADMIN:
            if requested_firm_id is None:
                raise HTTPException(
                    status_code=400,
                    detail="super_admin must specify firm_id explicitly — there is no "
                    "implicit 'own firm' for a platform-level user.",
                )
            return requested_firm_id

        # firm_admin: always their own firm, regardless of what (if anything)
        # was passed — never let a firm_admin act on another firm's billing.
        if requested_firm_id is not None and requested_firm_id != current_user.firm_id:
            raise HTTPException(
                status_code=403, detail="Cannot manage billing for another firm"
            )
        if current_user.firm_id is None:
            raise HTTPException(
                status_code=400, detail="Current user is not attached to a firm"
            )
        return current_user.firm_id

    def _validate_seats(self, plan: Plan, seats: int) -> None:
        if seats < 1:
            raise HTTPException(status_code=400, detail="seats must be at least 1")
        if seats < plan.min_seats:
            raise HTTPException(
                status_code=400,
                detail=f"{plan.name} requires at least {plan.min_seats} seat(s)",
            )
        if plan.max_seats is not None and seats > plan.max_seats:
            raise HTTPException(
                status_code=400,
                detail=f"{plan.name} supports at most {plan.max_seats} seat(s) — "
                f"contact us about the Enterprise tier for more.",
            )

    def get_active_subscription(self, current_user: User, firm_id: uuid.UUID | None) -> Subscription:
        resolved_firm_id = self._resolve_firm_id(current_user, firm_id)
        subscription = self.subscriptions.get_active_for_firm(resolved_firm_id)
        if not subscription:
            raise HTTPException(
                status_code=404, detail="This firm has no active subscription"
            )
        return subscription

    def list_subscriptions(self, current_user: User, firm_id: uuid.UUID | None) -> list[Subscription]:
        resolved_firm_id = self._resolve_firm_id(current_user, firm_id)
        return self.subscriptions.list_for_firm(resolved_firm_id)

    def create_subscription(self, payload: SubscriptionCreate, current_user: User) -> Subscription:
        firm_id = self._resolve_firm_id(current_user, payload.firm_id)

        existing = self.subscriptions.get_active_for_firm(firm_id)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This firm already has an active subscription — use the "
                "upgrade endpoint to change plan/seats instead.",
            )

        plan = self.plans.get_by_id(payload.plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=404, detail="Plan not found or inactive")
        self._validate_seats(plan, payload.seats)

        if plan.tier == PlanTier.ENTERPRISE:
            # Custom-priced tier — no self-serve checkout. A real deployment
            # would route this to a sales-assisted flow rather than the
            # gateway integration below.
            raise HTTPException(
                status_code=400,
                detail="Enterprise plans are set up by the TaxFlow team, not self-serve — "
                "please get in touch.",
            )

        # TODO(payment-gateway): before marking this ACTIVE for a paid tier,
        # a real deployment would create a customer + subscription on the
        # gateway (Razorpay, if that's confirmed as the choice — see this
        # module's docstring) and only flip to ACTIVE on a successful
        # payment/webhook confirmation, storing the gateway's subscription id
        # in payment_gateway_ref. FREE tier has no such step. Until a gateway
        # exists, every subscription is created ACTIVE directly.
        today = date.today()
        subscription = Subscription(
            firm_id=firm_id,
            plan_id=plan.id,
            seats=payload.seats,
            billing_period=payload.billing_period,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=today,
            current_period_end=_period_end(today, payload.billing_period),
        )
        return self.subscriptions.create(subscription)

    def upgrade_subscription(
        self, payload: SubscriptionUpgrade, current_user: User, firm_id: uuid.UUID | None
    ) -> Subscription:
        """Changes plan and/or seats on the firm's current subscription
        in-place (does not start a new billing period or reset
        current_period_end) — a real gateway integration would additionally
        prorate the difference; that proration logic lives at the
        TODO(payment-gateway) marker below, not here, since it depends on
        the gateway's own proration semantics."""
        subscription = self.get_active_subscription(current_user, firm_id)

        new_plan = subscription.plan
        if payload.plan_id is not None and payload.plan_id != subscription.plan_id:
            new_plan = self.plans.get_by_id(payload.plan_id)
            if not new_plan or not new_plan.is_active:
                raise HTTPException(status_code=404, detail="Plan not found or inactive")
            if new_plan.tier == PlanTier.ENTERPRISE:
                raise HTTPException(
                    status_code=400,
                    detail="Enterprise plans are set up by the TaxFlow team, not self-serve — "
                    "please get in touch.",
                )
            subscription.plan_id = new_plan.id

        new_seats = payload.seats if payload.seats is not None else subscription.seats
        self._validate_seats(new_plan, new_seats)
        subscription.seats = new_seats

        if payload.billing_period is not None:
            subscription.billing_period = payload.billing_period

        # TODO(payment-gateway): prorate/charge the difference in cost here
        # (new seats * new plan price vs. what was already paid for the rest
        # of the current period) once a gateway is wired up.
        return self.subscriptions.update(subscription)

    def cancel_subscription(
        self, payload: SubscriptionCancel, current_user: User, firm_id: uuid.UUID | None
    ) -> Subscription:
        subscription = self.get_active_subscription(current_user, firm_id)

        if payload.at_period_end:
            subscription.cancel_at_period_end = True
        else:
            # TODO(payment-gateway): cancel the gateway-side subscription
            # immediately here too, once one exists, so the firm isn't billed
            # for a period they no longer have access to.
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = date.today()

        return self.subscriptions.update(subscription)


def process_subscription_period_rollovers(db: Session) -> dict:
    """Run periodically (see app.worker.tasks.expire_subscriptions) to act on
    subscriptions whose current_period_end has passed. No payment gateway is
    wired up (see module docstring), so this never silently renews a paid
    period — it only:
      - cancels subscriptions with cancel_at_period_end set, or
      - marks other expired ACTIVE/TRIALING subscriptions PAST_DUE, since a
        renewal charge can't actually be confirmed.
    PAST_DUE/CANCELLED rows are left alone (already handled).
    """
    repo = SubscriptionRepository(db)
    today = date.today()
    cancelled = 0
    past_due = 0

    for subscription in repo.list_past_period_end(as_of=today):
        if subscription.cancel_at_period_end:
            subscription.status = SubscriptionStatus.CANCELLED
            subscription.cancelled_at = today
            cancelled += 1
        elif subscription.status != SubscriptionStatus.PAST_DUE:
            subscription.status = SubscriptionStatus.PAST_DUE
            past_due += 1
        repo.update(subscription)

    return {"cancelled": cancelled, "past_due": past_due}
