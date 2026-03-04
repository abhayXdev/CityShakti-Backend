"""add_email_otps_table

Revision ID: f1abc1234567
Revises: e949afcd2476
Create Date: 2026-03-04 19:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1abc1234567'
down_revision = 'e949afcd2476'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'email_otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('otp_code', sa.String(), nullable=True),
        sa.Column('is_used', sa.Boolean(), nullable=True, default=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_email_otps_email'), 'email_otps', ['email'], unique=False)
    op.create_index(op.f('ix_email_otps_id'), 'email_otps', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_otps_id'), table_name='email_otps')
    op.drop_index(op.f('ix_email_otps_email'), table_name='email_otps')
    op.drop_table('email_otps')
