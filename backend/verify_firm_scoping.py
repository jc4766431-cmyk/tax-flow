"""
Live two-firm verification for §0e (clients/documents) and §0f (tasks)
firm-scoping fixes, per NEXT-PROMPT.md's instructions. Run against a live
uvicorn + Postgres. Prints PASS/FAIL for each check; exits non-zero on any
failure.
"""
import sys
import httpx

BASE = "http://localhost:8000/api/v1"
FIRM_A = "6fc8f3d3-c960-4505-9295-019510b6002d"
FIRM_B = "28bdbc23-95cc-46b8-956d-4c25ba84919b"

results = []


def check(name, cond):
    results.append((name, cond))
    print(("PASS" if cond else "FAIL") + " - " + name)


c = httpx.Client(base_url=BASE, timeout=10)


def register(email, role, firm_id):
    r = c.post("/auth/register", json={
        "email": email, "password": "TestPass123!", "full_name": "Test User",
        "role": role, "firm_id": firm_id,
    })
    assert r.status_code in (200, 201), r.text
    r2 = c.post("/auth/login", json={"email": email, "password": "TestPass123!"})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


# --- setup: accountant tokens for firm A and firm B, plus a super_admin ---
tok_a = register("acct.a@test.com", "accountant", FIRM_A)
tok_b = register("acct.b@test.com", "accountant", FIRM_B)
tok_super = register("super@test.com", "super_admin", None)

hdr_a = {"Authorization": f"Bearer {tok_a}"}
hdr_b = {"Authorization": f"Bearer {tok_b}"}
hdr_super = {"Authorization": f"Bearer {tok_super}"}

# --- clients: create one client-role user, then the Client record under firm A ---
r = c.post("/auth/register", json={
    "email": "clienta1@test.com", "password": "TestPass123!", "full_name": "Client A1",
    "role": "client", "firm_id": None,
})
assert r.status_code in (200, 201), r.text
client_user_id = r.json()["id"]

# accountant A tries to create the client, attempting to set firm_id to FIRM_B (attacker-settable check)
r = c.post("/clients", json={
    "user_id": client_user_id, "firm_id": FIRM_B, "company_name": "Client A1 Co",
}, headers=hdr_a)
check("POST /clients as accountant A -> 201", r.status_code == 201)
client_a = r.json()
check("client created is scoped to firm A regardless of firm_id in payload (not attacker-settable)",
      client_a.get("firm_id") == FIRM_A)

# accountant B tries to read firm A's client
r = c.get(f"/clients/{client_a['id']}", headers=hdr_b)
check("GET /clients/{id} as accountant B on firm A's client -> 403 (not empty/404)",
      r.status_code == 403)

# accountant B lists clients -> should not include firm A's client
r = c.get("/clients", headers=hdr_b)
check("GET /clients as accountant B -> 200", r.status_code == 200)
ids_b = [x["id"] for x in r.json().get("items", r.json() if isinstance(r.json(), list) else [])]
check("GET /clients as accountant B does not include firm A's client", client_a["id"] not in ids_b)

# super_admin can read it
r = c.get(f"/clients/{client_a['id']}", headers=hdr_super)
check("GET /clients/{id} as super_admin on any firm's client -> 200", r.status_code == 200)

# --- tasks: accountant A creates a client-less task ---
r = c.post("/tasks", json={"title": "Follow up A"}, headers=hdr_a)
check("POST /tasks (no client_id) as accountant A -> 201", r.status_code == 201)
task_a = r.json()
check("client-less task inherits creator's firm_id", task_a.get("firm_id") == FIRM_A)

# accountant A creates a task tied to their client
r = c.post("/tasks", json={"title": "Review docs A1", "client_id": client_a["id"]}, headers=hdr_a)
check("POST /tasks (with client_id) as accountant A -> 201", r.status_code == 201)
task_a2 = r.json()
check("client-tied task resolves firm_id from the client", task_a2.get("firm_id") == FIRM_A)

# accountant B tries to read/act on firm A's task -> 403
r = c.get(f"/tasks/{task_a['id']}", headers=hdr_b)
check("GET /tasks/{id} as accountant B on firm A's task -> 403 (not empty/404)", r.status_code == 403)

r = c.patch(f"/tasks/{task_a['id']}/status", json={"status": "review"}, headers=hdr_b)
check("PATCH /tasks/{id}/status as accountant B on firm A's task -> 403", r.status_code == 403)

r = c.delete(f"/tasks/{task_a['id']}", headers=hdr_b)
check("DELETE /tasks/{id} as accountant B on firm A's task -> 403", r.status_code == 403)

# accountant B lists tasks/board -> should not include firm A's tasks
r = c.get("/tasks", headers=hdr_b)
check("GET /tasks as accountant B -> 200", r.status_code == 200)
task_ids_b = [t["id"] for t in r.json()]
check("GET /tasks as accountant B does not include firm A's tasks",
      task_a["id"] not in task_ids_b and task_a2["id"] not in task_ids_b)

r = c.get("/tasks/board", headers=hdr_b)
check("GET /tasks/board as accountant B -> 200", r.status_code == 200)
board_b_ids = [t["id"] for col in r.json()["columns"].values() for t in col]
check("GET /tasks/board as accountant B does not include firm A's tasks",
      task_a["id"] not in board_b_ids and task_a2["id"] not in board_b_ids)

# accountant A can still access their own task fine
r = c.get(f"/tasks/{task_a['id']}", headers=hdr_a)
check("GET /tasks/{id} as accountant A on own firm's task -> 200", r.status_code == 200)

# super_admin cross-firm access to tasks still works
r = c.get(f"/tasks/{task_a['id']}", headers=hdr_super)
check("GET /tasks/{id} as super_admin on any firm's task -> 200", r.status_code == 200)

r = c.get("/tasks", headers=hdr_super)
check("GET /tasks as super_admin -> 200", r.status_code == 200)
all_ids = [t["id"] for t in r.json()]
check("GET /tasks as super_admin includes firm A's tasks (cross-firm)", task_a["id"] in all_ids)

# super_admin creating a client-less task -> rejected per §0f design (no firm to fall back to)
r = c.post("/tasks", json={"title": "Orphan task"}, headers=hdr_super)
check("POST /tasks (no client_id) as super_admin -> 400 (no firm to fall back to)",
      r.status_code == 400)

print()
failed = [n for n, ok in results if not ok]
if failed:
    print(f"{len(failed)} CHECK(S) FAILED:")
    for n in failed:
        print(" -", n)
    sys.exit(1)
else:
    print(f"ALL {len(results)} CHECKS PASSED")
