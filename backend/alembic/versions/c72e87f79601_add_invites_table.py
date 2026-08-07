"""add invites table

Revision ID: c72e87f79601
Revises: c2e5f7b03a12
Create Date: 2026-08-07 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c72e87f79601'
down_revision = 'c2e5f7b03a12'
branch_labels = None
depends_on = None

# userrole was already created as a PG enum type by the initial migration
# (for users.role) — reuse it here rather than letting autogenerate try to
# CREATE TYPE a second time. Same lesson as e8623919c959's
# _document_category/_document_status (see that migration / HANDOFF §0c bug #2).
_user_role = postgresql.ENUM(
    'SUPER_ADMIN', 'FIRM_ADMIN', 'ACCOUNTANT', 'REVIEWER', 'CLIENT',
    name='userrole', create_type=False,
)


def upgrade() -> None:
    op.create_table(
        'invites',
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('firm_id', sa.UUID(), nullable=False),
        sa.Column('role', _user_role, nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['firm_id'], ['firms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index(op.f('ix_invites_email'), 'invites', ['email'])
    op.create_index(op.f('ix_invites_firm_id'), 'invites', ['firm_id'])
    op.create_index(op.f('ix_invites_token'), 'invites', ['token'])


def downgrade() -> None:
    op.drop_index(op.f('ix_invites_token'), table_name='invites')
    op.drop_index(op.f('ix_invites_firm_id'), table_name='invites')
    op.drop_index(op.f('ix_invites_email'), table_name='invites')
    op.drop_table('invites')
