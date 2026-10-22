"""Make human-effort measurements explicit and non-overlapping.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exception_cases",
        sa.Column(
            "human_minutes_measured",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "pilot_log_entries",
        sa.Column(
            "human_minutes_measured",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )
    op.add_column(
        "pilot_log_entries",
        sa.Column("labor_accounting", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "pilot_log_entries",
        sa.Column("related_exception_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_pilot_log_related_exception",
        "pilot_log_entries",
        "exception_cases",
        ["related_exception_id"],
        ["id"],
    )
    op.create_index(
        "ix_pilot_log_entries_related_exception_id",
        "pilot_log_entries",
        ["related_exception_id"],
        unique=False,
    )
    op.create_check_constraint(
        "ck_pilot_log_labor_accounting",
        "pilot_log_entries",
        "labor_accounting IS NULL OR labor_accounting IN "
        "('additional', 'included_in_exception')",
    )
    op.create_check_constraint(
        "ck_pilot_log_included_requires_exception",
        "pilot_log_entries",
        "labor_accounting <> 'included_in_exception' OR related_exception_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_pilot_log_included_requires_exception",
        "pilot_log_entries",
        type_="check",
    )
    op.drop_constraint(
        "ck_pilot_log_labor_accounting",
        "pilot_log_entries",
        type_="check",
    )
    op.drop_index(
        "ix_pilot_log_entries_related_exception_id",
        table_name="pilot_log_entries",
    )
    op.drop_constraint(
        "fk_pilot_log_related_exception",
        "pilot_log_entries",
        type_="foreignkey",
    )
    op.drop_column("pilot_log_entries", "related_exception_id")
    op.drop_column("pilot_log_entries", "labor_accounting")
    op.drop_column("pilot_log_entries", "human_minutes_measured")
    op.drop_column("exception_cases", "human_minutes_measured")
