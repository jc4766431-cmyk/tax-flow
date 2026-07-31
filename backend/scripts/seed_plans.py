"""
Seed script for `plans` — closes NEXT-PROMPT.md's "must build before launch"
item 2 ("a Plan-seeding path ... so a fresh environment isn't permanently
stuck with zero plans until someone remembers to call POST /billing/plans
four times by hand").

Pricing/tiers are taken directly from STRATEGY_REVIEW.md Phase 7 — do not
change the numbers here without updating that doc too, they're meant to
stay in sync:
  - Free:       ₹0/seat, 1 seat, max_clients=5, hard-limited acquisition tier.
  - Solo:       ₹999/month flat (1 user).
  - Team:       ₹1,499/user/month, 2-10 users, monthly billing (no
                annual-only lock-in — a deliberate wedge against TaxDome
                per Phase 7).
  - Firm:       ₹1,999/user/month, 11-50 users. The compliance-risk engine
                add-on Phase 7 mentions is a separate future line item, not
                modeled as part of this row.
  - Enterprise: custom pricing (price_per_seat_inr left null = "contact
                us"), 51+ seats, no self-serve checkout (billing_service.py
                already rejects self-serve Enterprise signup).

Idempotent: safe to run repeatedly against the same database. For each
tier, if a Plan row already exists (Plan.tier is unique — see
app/models/billing.py), it is left untouched — this script only fills gaps,
it never overwrites an admin's later price/description edit made via
`PATCH /billing/plans/{id}`. Delete/recreate manually if you actually want
to reset a tier's seed values.

Usage (from `backend/`, with the same environment/venv the app itself
uses so `app.core.config.settings.DATABASE_URL` resolves correctly):

    python -m scripts.seed_plans

NOT run against a live database in this pass — see HANDOFF.md for the
current pass's verification scope. This script was written to match the
`Plan` model/schema exactly (re-read field-by-field against
app/models/billing.py and app/schemas/billing.py) and compiles cleanly
with `python3 -m py_compile`, but "seed the DB and confirm four (five)
rows land with the right fields" is still an open verification item —
see NEXT-PROMPT.md item 2/3.
"""
import logging
import sys

from app.db.session import SessionLocal
from app.models.billing import BillingPeriod, Plan, PlanTier
from app.repositories.billing_repository import PlanRepository

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_plans")

PLAN_SEEDS: list[dict] = [
    {
        "tier": PlanTier.FREE,
        "name": "Free",
        "description": (
            "Acquisition tier for solo CAs trying TaxFlow out — hard "
            "limits, no automation."
        ),
        "price_per_seat_inr": 0,
        "billing_period": BillingPeriod.MONTHLY,
        "min_seats": 1,
        "max_seats": 1,
        "max_clients": 5,
        "is_active": True,
    },
    {
        "tier": PlanTier.SOLO,
        "name": "Solo",
        "description": "For a single practitioner. Flat monthly price, unlimited clients.",
        "price_per_seat_inr": 999,
        "billing_period": BillingPeriod.MONTHLY,
        "min_seats": 1,
        "max_seats": 1,
        "max_clients": None,
        "is_active": True,
    },
    {
        "tier": PlanTier.TEAM,
        "name": "Team",
        "description": (
            "For small firms of 2-10 accountants. Monthly billing available "
            "— no annual lock-in required."
        ),
        "price_per_seat_inr": 1499,
        "billing_period": BillingPeriod.MONTHLY,
        "min_seats": 2,
        "max_seats": 10,
        "max_clients": None,
        "is_active": True,
    },
    {
        "tier": PlanTier.FIRM,
        "name": "Firm",
        "description": (
            "For firms of 11-50 accountants. Compliance-risk engine "
            "add-on priced and sold separately."
        ),
        "price_per_seat_inr": 1999,
        "billing_period": BillingPeriod.MONTHLY,
        "min_seats": 11,
        "max_seats": 50,
        "max_clients": None,
        "is_active": True,
    },
    {
        "tier": PlanTier.ENTERPRISE,
        "name": "Enterprise",
        "description": (
            "Custom pricing for 50+ seats / multi-branch firms. Includes "
            "white-label client portal and dedicated onboarding. Contact "
            "us — no self-serve checkout for this tier."
        ),
        "price_per_seat_inr": None,
        "billing_period": BillingPeriod.MONTHLY,
        "min_seats": 51,
        "max_seats": None,
        "max_clients": None,
        "is_active": True,
    },
]


def seed_plans() -> int:
    """Creates any missing Plan rows. Returns the number of rows created."""
    db = SessionLocal()
    created = 0
    try:
        repo = PlanRepository(db)
        for seed in PLAN_SEEDS:
            existing = repo.get_by_tier(seed["tier"])
            if existing:
                logger.info("skip  %-12s already exists (id=%s)", seed["tier"].value, existing.id)
                continue
            plan = Plan(**seed)
            repo.create(plan)
            created += 1
            logger.info("create %-12s id=%s price_per_seat_inr=%s", seed["tier"].value, plan.id, plan.price_per_seat_inr)
        return created
    finally:
        db.close()


if __name__ == "__main__":
    n = seed_plans()
    logger.info("Done. %d plan(s) created, %d already present.", n, len(PLAN_SEEDS) - n)
    sys.exit(0)
