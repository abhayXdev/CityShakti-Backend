"""add_ondelete_rules

Revision ID: g2bcd1234567
Revises: 66e6d841e84a
Create Date: 2026-03-28 00:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g2bcd1234567'
down_revision = '66e6d841e84a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Complaint.citizen_id
    op.drop_constraint('complaints_citizen_id_fkey', 'complaints', type_='foreignkey')
    op.create_foreign_key('complaints_citizen_id_fkey', 'complaints', 'users', ['citizen_id'], ['id'], ondelete='SET NULL')

    # 2. ComplaintActivity.actor_id
    op.drop_constraint('complaint_activities_actor_id_fkey', 'complaint_activities', type_='foreignkey')
    op.create_foreign_key('complaint_activities_actor_id_fkey', 'complaint_activities', 'users', ['actor_id'], ['id'], ondelete='SET NULL')

    # 3. ComplaintUpdate.created_by_id
    op.drop_constraint('complaint_updates_created_by_id_fkey', 'complaint_updates', type_='foreignkey')
    op.create_foreign_key('complaint_updates_created_by_id_fkey', 'complaint_updates', 'users', ['created_by_id'], ['id'], ondelete='SET NULL')

    # 4. ComplaintUpvote.user_id
    op.drop_constraint('complaint_upvotes_user_id_fkey', 'complaint_upvotes', type_='foreignkey')
    op.create_foreign_key('complaint_upvotes_user_id_fkey', 'complaint_upvotes', 'users', ['user_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    # 1. Complaint.citizen_id
    op.drop_constraint('complaints_citizen_id_fkey', 'complaints', type_='foreignkey')
    op.create_foreign_key('complaints_citizen_id_fkey', 'complaints', 'users', ['citizen_id'], ['id'])

    # 2. ComplaintActivity.actor_id
    op.drop_constraint('complaint_activities_actor_id_fkey', 'complaint_activities', type_='foreignkey')
    op.create_foreign_key('complaint_activities_actor_id_fkey', 'complaint_activities', 'users', ['actor_id'], ['id'])

    # 3. ComplaintUpdate.created_by_id
    op.drop_constraint('complaint_updates_created_by_id_fkey', 'complaint_updates', type_='foreignkey')
    op.create_foreign_key('complaint_updates_created_by_id_fkey', 'complaint_updates', 'users', ['created_by_id'], ['id'])

    # 4. ComplaintUpvote.user_id
    op.drop_constraint('complaint_upvotes_user_id_fkey', 'complaint_upvotes', type_='foreignkey')
    op.create_foreign_key('complaint_upvotes_user_id_fkey', 'complaint_upvotes', 'users', ['user_id'], ['id'])
