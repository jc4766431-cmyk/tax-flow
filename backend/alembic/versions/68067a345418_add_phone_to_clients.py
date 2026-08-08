"""add phone to clients

Revision ID: 68067a345418
Revises: c72e87f79601
Create Date: 2026-08-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '68067a345418'
down_revision = 'c72e87f79601'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('phone', sa.String(length=30), nullable=True))
    op.create_index(op.f('ix_clients_phone'), 'clients', ['phone'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_clients_phone'), table_name='clients')
    op.drop_column('clients', 'phone')
