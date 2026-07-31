"""
Live verification for the billing/subscription module (HANDOFF.md §0i),
plus `scripts/seed_plans.py` (§0k part 1) as the source of the five `Plan`
rows this exercises. Run against a live uvicorn + Postgres, with
`python -m scripts.seed_plans` already run (or this script will find zero
plans and every check below will fail fast with a clear message rather than
a confusing 404 deep in the flow).

Prints PASS/FAIL for each check; exits non-zero on any failure.
"""
import sys
import uuid

import httpx

BASE = "http://localhost:8000/api/v1"
FIRM_A = "6fc8f3d3-c960-4505-9295-019510b6002d"
FIRM_B = "28bdbc23-95cc-46b8-956d-4c25ba84919b"

results = []


def check(name, cond, extra=""):
    results.append((name, cond))
    print(("PASS" if cond else "FAIL") + " - " + name + (f" ({extra})" if extra else ""))


c = httpx.Client(base_url=BASE, timeout=10)


def register(email, role, firm_id):
    r = c.post("/auth/register", json={
        "email": email, "password": "TestPass123!", "full_name": "Test User",
        "role": role, "firm_id": firm_id,
    })
    assert r.status_code in (200, 201), r.text
    tok = c.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert tok.status_code == 200, tok.text
    return tok.json()["access_token"]


def auth(tok):
    return {"Authorization": f"Bearer {tok}"}


suffix = uuid.uuid4().hex[:8]
admin_a = register(f"billing.admin.a.{suffix}@test.com", "firm_admin", FIRM_A)
admin_b = register(f"billing.admin.b.{suffix}@test.com", "firm_admin", FIRM_B)

# --- Plan catalog ---
plans_resp = c.get("/billing/plans", headers=auth(admin_a))
check("GET /billing/plans as firm_admin -> 200", plans_resp.status_code == 200, plans_resp.status_code)
plans = plans_resp.json() if plans_resp.status_code == 200 else []
by_tier = {p["tier"]: p for p in plans}
check(
    "seed_plans.py's five tiers are all present",
    {"free", "solo", "team", "firm", "enterprise"} <= set(by_tier.keys()),
    sorted(by_tier.keys()),
)
if len(by_tier) < 5:
    print("Cannot continue without all five seeded plans — run "
          "`python -m scripts.seed_plans` first.")
    sys.exit(1)

solo, team, enterprise = by_tier["solo"], by_tier["team"], by_tier["enterprise"]

# --- super_admin-only plan writes ---
create_plan_as_admin = c.post(
    "/billing/plans", headers=auth(admin_a),
    json={"tier": "free", "name": "x", "price_per_seat_inr": 0},
)
check(
    "POST /billing/plans as firm_admin -> 403 (super_admin only)",
    create_plan_as_admin.status_code == 403, create_plan_as_admin.status_code,
)

# --- Create subscription (firm A, Solo tier) ---
create_sub = c.post(
    "/billing/subscription", headers=auth(admin_a),
    json={"plan_id": solo["id"], "seats": 1, "billing_period": "monthly"},
)
check("POST /billing/subscription (Solo, firm A) -> 201", create_sub.status_code == 201, create_sub.text)
sub_a = create_sub.json() if create_sub.status_code == 201 else {}
check("created subscription is scoped to firm A", sub_a.get("firm_id") == FIRM_A, sub_a.get("firm_id"))
check("created subscription status is active", sub_a.get("status") == "active", sub_a.get("status"))

# --- Duplicate create should be rejected ---
dup = c.post(
    "/billing/subscription", headers=auth(admin_a),
    json={"plan_id": solo["id"], "seats": 1},
)
check("POST /billing/subscription again (firm A already has one) -> 400", dup.status_code == 400, dup.status_code)

# --- Enterprise is not self-serve ---
ent = c.post(
    "/billing/subscription", headers=auth(admin_b),
    json={"plan_id": enterprise["id"], "seats": 60},
)
check("POST /billing/subscription (Enterprise, firm B) -> 400 (not self-serve)", ent.status_code == 400, ent.status_code)

# --- Seat-limit validation (Team supports 2-10 seats) ---
too_few = c.post(
    "/billing/subscription", headers=auth(admin_b),
    json={"plan_id": team["id"], "seats": 1},
)
check("POST /billing/subscription (Team, 1 seat) -> 400 (below min_seats)", too_few.status_code == 400, too_few.status_code)

create_sub_b = c.post(
    "/billing/subscription", headers=auth(admin_b),
    json={"plan_id": team["id"], "seats": 3, "billing_period": "monthly"},
)
check("POST /billing/subscription (Team, 3 seats, firm B) -> 201", create_sub_b.status_code == 201, create_sub_b.text)

# --- Firm-scoping: firm B admin cannot read firm A's subscription ---
cross_firm_read = c.get("/billing/subscription", headers=auth(admin_b), params={"firm_id": FIRM_A})
check(
    "GET /billing/subscription?firm_id=<firm A> as firm B admin -> 403",
    cross_firm_read.status_code == 403, cross_firm_read.status_code,
)

own_read = c.get("/billing/subscription", headers=auth(admin_a))
check("GET /billing/subscription as firm A admin -> 200, own firm", own_read.status_code == 200 and own_read.json().get("firm_id") == FIRM_A)

# --- Upgrade ---
upgrade = c.patch(
    "/billing/subscription/upgrade", headers=auth(admin_a),
    json={"plan_id": team["id"], "seats": 2},
)
check("PATCH /billing/subscription/upgrade (Solo -> Team, 2 seats) -> 200", upgrade.status_code == 200, upgrade.text)
if upgrade.status_code == 200:
    body = upgrade.json()
    check("upgraded subscription now on Team plan", body.get("plan_id") == team["id"])
    check("upgraded subscription seats updated to 2", body.get("seats") == 2, body.get("seats"))

# seats below new plan's min_seats should be rejected
bad_upgrade = c.patch("/billing/subscription/upgrade", headers=auth(admin_a), json={"seats": 1})
check("PATCH /billing/subscription/upgrade to 1 seat on Team -> 400 (below min_seats)", bad_upgrade.status_code == 400, bad_upgrade.status_code)

# --- Cancel (at period end, default) ---
cancel = c.post("/billing/subscription/cancel", headers=auth(admin_a), json={})
check("POST /billing/subscription/cancel (default at_period_end) -> 200", cancel.status_code == 200, cancel.text)
if cancel.status_code == 200:
    body = cancel.json()
    check("cancel_at_period_end set true, status still active", body.get("cancel_at_period_end") is True and body.get("status") == "active")

# --- History ---
history = c.get("/billing/subscription/history", headers=auth(admin_a))
check("GET /billing/subscription/history as firm A admin -> 200, non-empty", history.status_code == 200 and len(history.json()) >= 1)

# --- Immediate cancel on firm B's subscription ---
cancel_now = c.post("/billing/subscription/cancel", headers=auth(admin_b), json={"at_period_end": False})
check("POST /billing/subscription/cancel (immediate) firm B -> 200, status cancelled", cancel_now.status_code == 200 and cancel_now.json().get("status") == "cancelled")

get_after_cancel = c.get("/billing/subscription", headers=auth(admin_b))
check("GET /billing/subscription after immediate cancel -> 404 (no active sub)", get_after_cancel.status_code == 404, get_after_cancel.status_code)

print()
failed = [n for n, ok in results if not ok]
if failed:
    print(f"{len(failed)} CHECK(S) FAILED: {failed}")
    sys.exit(1)
print(f"ALL {len(results)} CHECKS PASSED")
