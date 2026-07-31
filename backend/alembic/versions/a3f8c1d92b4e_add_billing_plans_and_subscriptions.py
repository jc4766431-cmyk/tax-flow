"""add billing plans and subscriptions tables

Revision ID: a3f8c1d92b4e
Revises: 59e190e569ff
Create Date: 2026-07-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3f8c1d92b4e'
down_revision = '59e190e569ff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'plans',
        sa.Column('tier', sa.Enum('FREE', 'SOLO', 'TEAM', 'FIRM', 'ENTERPRISE', name='plantier'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('price_per_seat_inr', sa.Numeric(10, 2), nullable=True),
        sa.Column('billing_period', sa.Enum('MONTHLY', 'ANNUAL', name='billingperiod'), nullable=False),
        sa.Column('min_seats', sa.Integer(), nullable=False),
        sa.Column('max_seats', sa.Integer(), nullable=True),
        sa.Column('max_clients', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tier'),
    )

    op.create_table(
        'subscriptions',
        sa.Column('firm_id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('seats', sa.Integer(), nullable=False),
        sa.Column('billing_period', sa.Enum('MONTHLY', 'ANNUAL', name='billingperiod'), nullable=False),
        sa.Column(
            'status',
            sa.Enum('TRIALING', 'ACTIVE', 'PAST_DUE', 'CANCELLED', name='subscriptionstatus'),
            nullable=False,
        ),
        sa.Column('current_period_start', sa.Date(), nullable=False),
        sa.Column('current_period_end', sa.Date(), nullable=False),
        sa.Column('cancel_at_period_end', sa.Boolean(), nullable=False),
        sa.Column('cancelled_at', sa.Date(), nullable=True),
        sa.Column('payment_gateway_ref', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['firms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_subscriptions_firm_id'), 'subscriptions', ['firm_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_subscriptions_firm_id'), table_name='subscriptions')
    op.drop_table('subscriptions')
    op.drop_table('plans')
    op.execute('DROP TYPE IF EXISTS subscriptionstatus')
    op.execute('DROP TYPE IF EXISTS billingperiod')
    op.execute('DROP TYPE IF EXISTS plantier')
