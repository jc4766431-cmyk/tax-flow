"""
Demo seed script — closes the §5 "deliberately deferred" gap: "no
scripts/seed.py or similar exists yet to populate a fresh DB with a demo
firm/clients/filings for frontend development."

Distinct from `scripts/seed_plans.py` (which seeds the platform's own
billing tiers) — this seeds one demo *firm* and its staff/clients/filings/
tasks so a fresh DB has real data to develop the frontend against, instead
of creating everything by hand through the API.

Idempotent: looks up the demo firm by name first; if it already exists,
does nothing further (does not duplicate or reset data on re-run).

Usage (from `backend/`, same venv as the app):

    python -m scripts.seed_demo

Not run against a live database in this pass, per this pass's explicit
"no testing/verification" instruction — re-read against
app/models/{user,client,filing,workflow}.py field-by-field, and compiles
cleanly with `python3 -m py_compile`, but run it yourself against a real
Postgres before trusting the rows land as described.
"""
import logging
import sys
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.client import Client
from app.models.filing import FilingRequest, FilingStage, FilingType
from app.models.user import Firm, User, UserRole
from app.models.workflow import Task, TaskStatus

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed_demo")

DEMO_FIRM_NAME = "Ledger & Co."
DEMO_PASSWORD = "DemoPass123!"


def seed_demo() -> bool:
    """Creates the demo firm + staff + clients + filings + tasks if the demo
    firm doesn't already exist. Returns True if it created new data."""
    db = SessionLocal()
    try:
        existing = db.scalar(select(Firm).where(Firm.name == DEMO_FIRM_NAME))
        if existing:
            logger.info("skip: demo firm %r already exists (id=%s)", DEMO_FIRM_NAME, existing.id)
            return False

        firm = Firm(name=DEMO_FIRM_NAME, legal_name="Ledger & Co. Chartered Accountants", is_active=True)
        db.add(firm)
        db.flush()

        admin = User(
            email="admin@demo.taxflow.test",
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Asha Rao",
            role=UserRole.FIRM_ADMIN,
            firm_id=firm.id,
            is_active=True,
            is_email_verified=True,
        )
        accountant = User(
            email="accountant@demo.taxflow.test",
            hashed_password=hash_password(DEMO_PASSWORD),
            full_name="Vikram Shah",
            role=UserRole.ACCOUNTANT,
            firm_id=firm.id,
            is_active=True,
            is_email_verified=True,
        )
        db.add_all([admin, accountant])
        db.flush()

        demo_clients = [
            ("priya@demo.taxflow.test", "Priya Nair", "Nair Textiles", "ABCDE1234F", "27ABCDE1234F1Z5"),
            ("rohit@demo.taxflow.test", "Rohit Mehta", "Mehta Consulting", "PQRSX5678L", None),
        ]

        client_rows = []
        for email, name, company, pan, gstin in demo_clients:
            user = User(
                email=email,
                hashed_password=hash_password(DEMO_PASSWORD),
                full_name=name,
                role=UserRole.CLIENT,
                firm_id=firm.id,
                is_active=True,
                is_email_verified=True,
            )
            db.add(user)
            db.flush()

            client = Client(
                user_id=user.id,
                firm_id=firm.id,
                company_name=company,
                pan_number=pan,
                gstin=gstin,
                assigned_accountant_id=accountant.id,
            )
            db.add(client)
            db.flush()
            client_rows.append(client)

        # One filing per client, in different stages, plus a matching Kanban task.
        filing_specs = [
            (FilingType.INCOME_TAX_RETURN, FilingStage.UNDER_REVIEW, TaskStatus.REVIEW),
            (FilingType.GST_RETURN, FilingStage.REQUESTED, TaskStatus.NEW),
        ]
        for client, (filing_type, stage, task_status) in zip(client_rows, filing_specs):
            filing = FilingRequest(
                client_id=client.id,
                filing_type=filing_type,
                stage=stage,
                assigned_accountant_id=accountant.id,
                period_label="FY 2025-26",
                due_date=date.today() + timedelta(days=30),
            )
            db.add(filing)
            db.flush()

            db.add(Task(
                title=f"{filing_type.value.replace('_', ' ').title()} — {client.company_name}",
                status=task_status,
                firm_id=firm.id,
                client_id=client.id,
                filing_request_id=filing.id,
                assigned_to_id=accountant.id,
                due_date=None,
            ))

        db.commit()
        logger.info(
            "created demo firm %r with 2 staff, %d clients, %d filings/tasks",
            DEMO_FIRM_NAME, len(client_rows), len(filing_specs),
        )
        logger.info("login for any seeded user: <email> / %s", DEMO_PASSWORD)
        return True
    finally:
        db.close()


if __name__ == "__main__":
    created = seed_demo()
    sys.exit(0)
