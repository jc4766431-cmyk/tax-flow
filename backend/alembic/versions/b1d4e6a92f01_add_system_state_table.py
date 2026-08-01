"""add system_state table

Revision ID: b1d4e6a92f01
Revises: f4a9c0e2b7d1
Create Date: 2026-08-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'b1d4e6a92f01'
down_revision = 'f4a9c0e2b7d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'system_state',
        sa.Column('key', sa.String(length=255), nullable=False),
        sa.Column('value', sa.String(length=1000), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('system_state')
