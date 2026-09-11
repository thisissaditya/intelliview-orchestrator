"""add timezone column to interview_schedules

Revision ID: 3be035abbe7b
Revises: ba859ad28cca
Create Date: 2026-09-11 08:00:57.572840

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3be035abbe7b'
down_revision: Union[str, Sequence[str], None] = 'ba859ad28cca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'interview_schedules',
        sa.Column('timezone', sa.String(64), nullable=False, server_default='UTC')
    )


def downgrade() -> None:
    op.drop_column('interview_schedules', 'timezone')