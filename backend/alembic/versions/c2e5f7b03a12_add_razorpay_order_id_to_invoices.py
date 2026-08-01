"""add razorpay_order_id to invoices

Revision ID: c2e5f7b03a12
Revises: b1d4e6a92f01
Create Date: 2026-08-01 00:05:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'c2e5f7b03a12'
down_revision = 'b1d4e6a92f01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('invoices', sa.Column('razorpay_order_id', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('invoices', 'razorpay_order_id')
