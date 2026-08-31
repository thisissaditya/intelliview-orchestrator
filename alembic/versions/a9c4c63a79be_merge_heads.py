"""merge heads

Revision ID: a9c4c63a79be
Revises: 003_add_candidate_features, aa56afa4b0bc
Create Date: 2026-08-28 22:35:13.855443

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "a9c4c63a79be"
down_revision: str | Sequence[str] | None = (
    "003_add_candidate_features",
    "aa56afa4b0bc",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""


def downgrade() -> None:
    """Downgrade schema."""
