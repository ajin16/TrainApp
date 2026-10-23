"""add_archived_fields_to_booking

Revision ID: 06b304215926
Revises: 
Create Date: 2026-10-24 00:56:14.283699

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '06b304215926'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.text('0')))
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_column('archived_at')
        batch_op.drop_column('is_archived')
