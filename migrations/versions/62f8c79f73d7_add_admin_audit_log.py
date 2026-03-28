"""add_admin_audit_log

Revision ID: 62f8c79f73d7
Revises: d8ccecacfe0e
Create Date: 2026-03-27 23:40:06.003157

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '62f8c79f73d7'
down_revision = 'd8ccecacfe0e'
branch_labels = None
depends_on = None


def upgrade():
    # Only create the admin_audit_log table.  All other tables were already
    # created by the preceding migration (d8ccecacfe0e).  Recreating them here
    # would raise duplicate-table errors on any database that has already been
    # migrated to d8ccecacfe0e.
    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['user.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['target_user_id'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('admin_audit_log')
