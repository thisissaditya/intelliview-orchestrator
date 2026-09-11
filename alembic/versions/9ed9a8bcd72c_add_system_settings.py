"""add system settings

Revision ID: 9ed9a8bcd72c
Revises: 002_add_llm_usage
Create Date: 2026-08-09 20:08:52.600484

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9ed9a8bcd72c"
down_revision: str | Sequence[str] | None = "002_add_llm_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the system_settings table."""
    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "default_theme",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "scheduling_strategy",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop the system_settings table."""
    op.drop_table("system_settings")
