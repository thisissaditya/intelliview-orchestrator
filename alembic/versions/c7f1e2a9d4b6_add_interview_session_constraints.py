"""add missing interview session constraints

Revision ID: c7f1e2a9d4b6
Revises: a9c4c63a79be
Create Date: 2026-09-05
"""

from alembic import op

revision = "c7f1e2a9d4b6"
down_revision = "ba859ad28cca"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_interview_status",
        "interview_sessions",
        """status IN (
            'pending',
            'CREATED',
            'QUEUED',
            'VIDEO_PROCESSING',
            'AUDIO_PROCESSING',
            'EVALUATING',
            'PROCESSING',
            'COMPLETED',
            'FAILED',
            'TIMEOUT',
            'CANCELLED'
        )""",
    )

    op.create_check_constraint(
        "ck_risk_score_non_negative",
        "interview_sessions",
        "risk_score IS NULL OR risk_score >= 0",
    )

    op.create_check_constraint(
        "ck_overall_score_non_negative",
        "interview_sessions",
        "overall_score IS NULL OR overall_score >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_overall_score_non_negative",
        "interview_sessions",
        type_="check",
    )

    op.drop_constraint(
        "ck_risk_score_non_negative",
        "interview_sessions",
        type_="check",
    )

    op.drop_constraint(
        "ck_interview_status",
        "interview_sessions",
        type_="check",
    )
