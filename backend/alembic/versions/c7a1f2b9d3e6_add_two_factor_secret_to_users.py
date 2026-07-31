"""add two_factor_secret to users

Revision ID: c7a1f2b9d3e6
Revises: a3f8c1d92b4e
Create Date: 2026-07-31 00:00:00.000000

Part of the TOTP two-factor-auth build flagged as open in HANDOFF.md
("Two-factor auth (`two_factor_enabled` field exists on `User`) has no
actual TOTP implementation. Use `pyotp` if you build this."). Stores the
base32 TOTP secret; `two_factor_enabled` already existed. Not run against
a live DB this pass — see HANDOFF.md for the verification still needed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c7a1f2b9d3e6'
down_revision = 'a3f8c1d92b4e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('two_factor_secret', sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'two_factor_secret')
