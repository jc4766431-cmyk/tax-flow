"""add firm_id to tasks

Revision ID: 88573fd4aed2
Revises: e8623919c959
Create Date: 2026-07-31 00:00:00.000000

Part of the Tasks/Kanban firm-scoping fix flagged as an open gap in
HANDOFF.md §0e — see task_service.py / app/api/deps.py for the enforcement
side of this change.

Added nullable (not NOT NULL) on purpose: this sandbox has no network
egress and no live Postgres to run this against, so there's no way to
backfill firm_id on any pre-existing task rows as part of this same
migration. Nullable is the honest choice given that constraint — do not
tighten this to nullable=False in a follow-up migration until you've
confirmed (in an environment with a live DB) that every existing row has
been backfilled, e.g.:

    UPDATE tasks SET firm_id = clients.firm_id
    FROM clients WHERE tasks.client_id = clients.id AND tasks.firm_id IS NULL;

    -- any tasks with no client_id and no firm_id at that point need a
    -- manual decision (which firm do they belong to?) before you can go
    -- NOT NULL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '88573fd4aed2'
down_revision = 'e8623919c959'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tasks', sa.Column('firm_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_tasks_firm_id_firms', 'tasks', 'firms', ['firm_id'], ['id'], ondelete='CASCADE'
    )
    op.create_index('ix_tasks_firm_id', 'tasks', ['firm_id'])


def downgrade() -> None:
    op.drop_index('ix_tasks_firm_id', table_name='tasks')
    op.drop_constraint('fk_tasks_firm_id_firms', 'tasks', type_='foreignkey')
    op.drop_column('tasks', 'firm_id')
