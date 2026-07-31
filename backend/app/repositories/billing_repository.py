"""
Repository pattern: isolates SQLAlchemy queries from business logic
(billing_service.py), matching task_repository.py / document_repository.py.
"""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.billing import Plan, PlanTier, Subscription, SubscriptionStatus


class PlanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: uuid.UUID) -> Plan | None:
        return self.db.get(Plan, plan_id)

    def get_by_tier(self, tier: PlanTier) -> Plan | None:
        return self.db.scalar(select(Plan).where(Plan.tier == tier))

    def list_plans(self, *, active_only: bool = True) -> list[Plan]:
        stmt = select(Plan)
        if active_only:
            stmt = stmt.where(Plan.is_active.is_(True))
        stmt = stmt.order_by(Plan.price_per_seat_inr.asc().nullslast())
        return list(self.db.scalars(stmt).all())

    def create(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def update(self, plan: Plan) -> Plan:
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, subscription_id: uuid.UUID) -> Subscription | None:
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.id == subscription_id)
        )
        return self.db.scalar(stmt)

    def get_active_for_firm(self, firm_id: uuid.UUID) -> Subscription | None:
        """The firm's current subscription: the non-cancelled row with the
        latest current_period_end, so a just-upgraded subscription (a new
        row, per create_subscription's history-preserving design) always
        wins over an older still-technically-non-cancelled one."""
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(
                Subscription.firm_id == firm_id,
                Subscription.status != SubscriptionStatus.CANCELLED,
            )
            .order_by(Subscription.current_period_end.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def list_past_period_end(self, *, as_of: date) -> list[Subscription]:
        """Non-cancelled subscriptions whose current_period_end has already
        passed, for the period-rollover task (billing_service.
        process_subscription_period_rollovers) to act on."""
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(
                Subscription.status != SubscriptionStatus.CANCELLED,
                Subscription.current_period_end < as_of,
            )
        )
        return list(self.db.scalars(stmt).all())

    def list_for_firm(self, firm_id: uuid.UUID) -> list[Subscription]:
        stmt = (
            select(Subscription)
            .options(joinedload(Subscription.plan))
            .where(Subscription.firm_id == firm_id)
            .order_by(Subscription.created_at.desc())
        )
        return list(self.db.scalars(stmt).all())

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def update(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription
