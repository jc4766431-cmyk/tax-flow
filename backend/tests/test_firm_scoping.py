"""
Automated regression coverage for the multi-tenant firm-scoping RBAC fix
(app/api/deps.py::assert_firm_scoped) and the related register
privilege-escalation fix found while writing this suite.

This is the "actual automated test... this is the one regression that
must never silently reappear" asked for in the Phase 1 prompt, replacing
the old manual `verify_firm_scoping.py` script (kept in the repo for
reference/manual runs, but this file is now the source of truth — it runs
in CI, that script doesn't).

Run with a real local Postgres available (see tests/conftest.py):
    pytest tests/test_firm_scoping.py -v
"""
from app.models.user import UserRole
from tests.conftest import auth_headers, make_firm, make_user


def test_accountant_b_cannot_read_firm_a_client(client, db):
    firm_a = make_firm(db, "Firm A")
    firm_b = make_firm(db, "Firm B")
    acct_a = make_user(db, email="acct.a@firm.test.example.com", role=UserRole.ACCOUNTANT, firm_id=firm_a.id)
    acct_b = make_user(db, email="acct.b@firm.test.example.com", role=UserRole.ACCOUNTANT, firm_id=firm_b.id)

    client_user = make_user(db, email="client.a1@firm.test.example.com", role=UserRole.CLIENT)

    r = client.post(
        "/api/v1/clients",
        json={"user_id": str(client_user.id), "firm_id": str(firm_b.id), "company_name": "Client A1 Co"},
        headers=auth_headers(acct_a),
    )
    assert r.status_code == 201, r.text
    client_a = r.json()
    # firm_id must be taken from the acting accountant's own firm, not the
    # (attacker-settable) payload value — this is the specific check the
    # original firm-scoping bug got wrong.
    assert client_a["firm_id"] == str(firm_a.id)

    r = client.get(f"/api/v1/clients/{client_a['id']}", headers=auth_headers(acct_b))
    assert r.status_code == 403, r.text

    r = client.get("/api/v1/clients", headers=auth_headers(acct_b))
    assert r.status_code == 200
    ids_b = [c["id"] for c in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
    assert client_a["id"] not in ids_b


def test_super_admin_bypasses_firm_scoping(client, db):
    firm_a = make_firm(db, "Firm A")
    acct_a = make_user(db, email="acct.a2@firm.test.example.com", role=UserRole.ACCOUNTANT, firm_id=firm_a.id)
    super_admin = make_user(db, email="super@firm.test.example.com", role=UserRole.SUPER_ADMIN)
    client_user = make_user(db, email="client.a2@firm.test.example.com", role=UserRole.CLIENT)

    r = client.post(
        "/api/v1/clients",
        json={"user_id": str(client_user.id), "firm_id": str(firm_a.id), "company_name": "Client A2 Co"},
        headers=auth_headers(acct_a),
    )
    assert r.status_code == 201
    client_a = r.json()

    r = client.get(f"/api/v1/clients/{client_a['id']}", headers=auth_headers(super_admin))
    assert r.status_code == 200, r.text


def test_accountant_b_cannot_read_or_modify_firm_a_tasks(client, db):
    firm_a = make_firm(db, "Firm A")
    firm_b = make_firm(db, "Firm B")
    acct_a = make_user(db, email="acct.a3@firm.test.example.com", role=UserRole.ACCOUNTANT, firm_id=firm_a.id)
    acct_b = make_user(db, email="acct.b3@firm.test.example.com", role=UserRole.ACCOUNTANT, firm_id=firm_b.id)
    super_admin = make_user(db, email="super3@firm.test.example.com", role=UserRole.SUPER_ADMIN)

    r = client.post("/api/v1/tasks", json={"title": "Follow up A"}, headers=auth_headers(acct_a))
    assert r.status_code == 201, r.text
    task_a = r.json()
    assert task_a["firm_id"] == str(firm_a.id)

    r = client.get(f"/api/v1/tasks/{task_a['id']}", headers=auth_headers(acct_b))
    assert r.status_code == 403

    r = client.patch(f"/api/v1/tasks/{task_a['id']}/status", json={"status": "review"}, headers=auth_headers(acct_b))
    assert r.status_code == 403

    r = client.delete(f"/api/v1/tasks/{task_a['id']}", headers=auth_headers(acct_b))
    assert r.status_code == 403

    r = client.get("/api/v1/tasks", headers=auth_headers(acct_b))
    assert r.status_code == 200
    assert task_a["id"] not in [t["id"] for t in r.json()]

    r = client.get("/api/v1/tasks/board", headers=auth_headers(acct_b))
    assert r.status_code == 200
    board_ids = [t["id"] for col in r.json()["columns"].values() for t in col]
    assert task_a["id"] not in board_ids

    # super_admin still has cross-firm access
    r = client.get(f"/api/v1/tasks/{task_a['id']}", headers=auth_headers(super_admin))
    assert r.status_code == 200

    r = client.get("/api/v1/tasks", headers=auth_headers(super_admin))
    assert r.status_code == 200
    assert task_a["id"] in [t["id"] for t in r.json()]


def test_super_admin_client_less_task_rejected(client, db):
    """super_admin has no firm_id to fall back to when creating a
    client-less task — §0f's documented, intentional 400, not a 500/edge
    case."""
    super_admin = make_user(db, email="super4@firm.test.example.com", role=UserRole.SUPER_ADMIN)
    r = client.post("/api/v1/tasks", json={"title": "Orphan task"}, headers=auth_headers(super_admin))
    assert r.status_code == 400


def test_register_cannot_self_assign_role_or_firm(client, db):
    """Regression test for the privilege-escalation hole found while
    building this suite: POST /auth/register used to accept `role` and
    `firm_id` straight from the request body with no auth check at all,
    letting any anonymous caller mint themselves a super_admin account or
    attach themselves to an arbitrary firm — which would make every check
    above meaningless, since there'd be no need to defeat firm-scoping if
    you can just register as super_admin directly. See UserRegister's
    docstring in app/schemas/auth.py."""
    firm = make_firm(db, "Firm C")

    r = client.post(
        "/api/v1/auth/register",
        json={
            "email": "wannabe.admin@firm.test.example.com",
            "password": "TestPass123!",
            "full_name": "Wannabe Admin",
            "role": "super_admin",
            "firm_id": str(firm.id),
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "client"
    assert body["firm_id"] is None
