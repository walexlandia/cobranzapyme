"""Measure human effort spent reviewing reconciliation proposals.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reconciliation_proposals",
        sa.Column("human_minutes", sa.Numeric(10, 2), nullable=True),
    )
    op.create_check_constraint(
        "ck_reconciliation_human_minutes",
        "reconciliation_proposals",
        "human_minutes IS NULL OR (human_minutes >= 0 AND human_minutes <= 480)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_reconciliation_human_minutes",
        "reconciliation_proposals",
        type_="check",
    )
    op.drop_column("reconciliation_proposals", "human_minutes")
