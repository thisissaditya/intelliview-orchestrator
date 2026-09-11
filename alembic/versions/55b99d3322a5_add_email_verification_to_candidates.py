"""add email verification to candidates

Revision ID: 55b99d3322a5
Revises: ba062b2def4d
Create Date: 2026-08-26 18:12:14.486878

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "55b99d3322a5"
down_revision: str | Sequence[str] | None = "ba062b2def4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add email verification fields to candidates."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {col["name"] for col in inspector.get_columns("candidates")}
    existing_indexes = {
        ix["name"] for ix in inspector.get_indexes("candidates") if ix.get("name")
    }
    if "email_verified" not in existing_columns:
        op.add_column(
            "candidates",
            sa.Column(
                "email_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    if "verification_token" not in existing_columns:
        op.add_column(
            "candidates",
            sa.Column(
                "verification_token",
                sa.String(255),
                nullable=True,
            ),
        )
    if (
        "verification_token" in existing_columns
        and "ix_candidates_verification_token" not in existing_indexes
    ):
        op.create_index(
            "ix_candidates_verification_token",
            "candidates",
            ["verification_token"],
            unique=True,
        )

    if "verification_token_expires_at" not in existing_columns:
        op.add_column(
            "candidates",
            sa.Column(
                "verification_token_expires_at",
                sa.DateTime(),
                nullable=True,
            ),
        )


def downgrade() -> None:
    """Remove email verification fields from candidates."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "candidates" in tables:
        existing_columns = {col["name"] for col in inspector.get_columns("candidates")}
        existing_indexes = {
            ix["name"] for ix in inspector.get_indexes("candidates") if ix.get("name")
        }

        if "ix_candidates_verification_token" in existing_indexes:
            op.drop_index("ix_candidates_verification_token", table_name="candidates")
        if "verification_token_expires_at" in existing_columns:
            op.drop_column("candidates", "verification_token_expires_at")
        if "verification_token" in existing_columns:
            op.drop_column("candidates", "verification_token")
        if "email_verified" in existing_columns:
            op.drop_column("candidates", "email_verified")
