"""merge heads

Revision ID: 66e6d841e84a
Revises: 44ee9c3cadc3, f1abc1234567
Create Date: 2026-03-04 21:05:46.705193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '66e6d841e84a'
down_revision: Union[str, None] = ('44ee9c3cadc3', 'f1abc1234567')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
