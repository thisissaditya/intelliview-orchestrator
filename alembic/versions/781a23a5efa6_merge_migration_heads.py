"""merge migration heads

Revision ID: 781a23a5efa6
Revises: 3be035abbe7b, c7f1e2a9d4b6
Create Date: 2026-09-11 08:51:21.535069

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '781a23a5efa6'
down_revision: Union[str, Sequence[str], None] = ('3be035abbe7b', 'c7f1e2a9d4b6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
