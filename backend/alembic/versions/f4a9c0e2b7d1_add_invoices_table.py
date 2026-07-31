"""add invoices table

Revision ID: f4a9c0e2b7d1
Revises: c7a1f2b9d3e6
Create Date: 2026-07-31 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f4a9c0e2b7d1'
down_revision = 'c7a1f2b9d3e6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'invoices',
        sa.Column('firm_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column(
            'status',
            sa.Enum('DRAFT', 'SENT', 'PAID', 'OVERDUE', 'CANCELLED', name='invoicestatus'),
            nullable=False,
        ),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('paid_at', sa.Date(), nullable=True),
        sa.Column('line_items', postgresql.JSONB(), nullable=False),
        sa.Column('subtotal', sa.Numeric(12, 2), nullable=False),
        sa.Column('tax_rate', sa.Numeric(5, 2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('notes', sa.String(length=2000), nullable=True),
        sa.Column('payment_reference', sa.String(length=255), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['firms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
    )
    op.create_index(op.f('ix_invoices_firm_id'), 'invoices', ['firm_id'], unique=False)
    op.create_index(op.f('ix_invoices_client_id'), 'invoices', ['client_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoices_client_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_firm_id'), table_name='invoices')
    op.drop_table('invoices')
    op.execute('DROP TYPE IF EXISTS invoicestatus')
