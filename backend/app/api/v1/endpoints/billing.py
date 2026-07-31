"""
Subscription billing endpoints — the firm's own TaxFlow account. See
models/billing.py and services/billing_service.py for the full design notes
(distinct from client invoicing, no payment gateway wired up yet).

Plan management (create/update the sellable tiers) is super_admin-only —
these are platform-level pricing decisions, not something a firm_admin
should be able to change for themselves. Reading the plan catalog and
managing a firm's own subscription is require_admin (firm_admin or
super_admin), same tier as clients.py's create/list-clients routes.
"""
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin, require_roles
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.billing import (
    PlanCreate,
    PlanRead,
    PlanUpdate,
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionRead,
    SubscriptionUpgrade,
)
from app.services.billing_service import PlanService, SubscriptionService

router = APIRouter(prefix="/billing", tags=["billing"])

require_super_admin = require_roles(UserRole.SUPER_ADMIN)


@router.get("/plans", response_model=list[PlanRead])
def list_plans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    include_inactive: bool = Query(default=False),
):
    """Readable by any authenticated user (not just admins) — a firm_admin
    deciding whether to upgrade needs to see the catalog, and there's
    nothing sensitive in a public price list."""
    return PlanService(db).list_plans(active_only=not include_inactive)


@router.post(
    "/plans",
    response_model=PlanRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_super_admin)],
)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    return PlanService(db).create_plan(payload)


@router.patch(
    "/plans/{plan_id}",
    response_model=PlanRead,
    dependencies=[Depends(require_super_admin)],
)
def update_plan(plan_id: uuid.UUID, payload: PlanUpdate, db: Session = Depends(get_db)):
    return PlanService(db).update_plan(plan_id, payload)


@router.get("/subscription", response_model=SubscriptionRead, dependencies=[Depends(require_admin)])
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    firm_id: uuid.UUID | None = Query(
        default=None, description="super_admin only — inspect another firm's subscription"
    ),
):
    return SubscriptionService(db).get_active_subscription(current_user, firm_id)


@router.get(
    "/subscription/history",
    response_model=list[SubscriptionRead],
    dependencies=[Depends(require_admin)],
)
def list_subscription_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    firm_id: uuid.UUID | None = Query(default=None),
):
    return SubscriptionService(db).list_subscriptions(current_user, firm_id)


@router.post(
    "/subscription",
    response_model=SubscriptionRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SubscriptionService(db).create_subscription(payload, current_user)


@router.patch(
    "/subscription/upgrade",
    response_model=SubscriptionRead,
    dependencies=[Depends(require_admin)],
)
def upgrade_subscription(
    payload: SubscriptionUpgrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    firm_id: uuid.UUID | None = Query(default=None),
):
    return SubscriptionService(db).upgrade_subscription(payload, current_user, firm_id)


@router.post(
    "/subscription/cancel",
    response_model=SubscriptionRead,
    dependencies=[Depends(require_admin)],
)
def cancel_subscription(
    payload: SubscriptionCancel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    firm_id: uuid.UUID | None = Query(default=None),
):
    return SubscriptionService(db).cancel_subscription(payload, current_user, firm_id)
