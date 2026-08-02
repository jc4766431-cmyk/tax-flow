"""
Shared pytest fixtures.

Uses a real local Postgres database (not SQLite — this codebase relies on
JSONB/UUID columns that SQLite can't represent faithfully, per HANDOFF.md
§2g). DATABASE_URL is overridden to a dedicated `taxflow_test` database
*before* any `app.*` module is imported, since app/db/session.py builds its
engine from settings.DATABASE_URL at import time.

Test-data setup (firms, staff users) goes directly through SQLAlchemy
models, not through POST /auth/register — that endpoint deliberately no
longer accepts role/firm_id (see app/schemas/auth.py's UserRegister
docstring), so creating a firm_admin/accountant/super_admin for test setup
has to happen the same way a real deployment would: server-side, not via
public self-registration.
"""
import os
import uuid

import pytest
from alembic import command
from alembic.config import Config

TEST_DATABASE_URL = "postgresql://taxflow:taxflow_dev_password@localhost:5432/taxflow_test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.db.session import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import Firm, User, UserRole  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_db():
    """Runs the real alembic migration chain against taxflow_test once per
    session, then drops and recreates the schema so this run starts from a
    truly clean slate regardless of what a prior run left behind."""
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")

    cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncates all app tables between tests for isolation, without paying
    the cost of re-running migrations per test."""
    yield
    with engine.begin() as conn:
        table_names = [t.name for t in reversed(Base.metadata.sorted_tables)]
        if table_names:
            conn.exec_driver_sql(
                "TRUNCATE TABLE " + ", ".join(f'"{n}"' for n in table_names) + " CASCADE;"
            )


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


def make_firm(db, name="Test Firm") -> Firm:
    firm = Firm(name=name)
    db.add(firm)
    db.commit()
    db.refresh(firm)
    return firm


def make_user(db, *, email, role: UserRole, firm_id=None, password="TestPass123!") -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=email.split("@")[0],
        role=role,
        firm_id=firm_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user: User) -> dict:
    token = create_access_token(
        subject=str(user.id), role=user.role.value, firm_id=str(user.firm_id) if user.firm_id else None
    )
    return {"Authorization": f"Bearer {token}"}
