"""Add idempotent guided portfolio-review sessions for PM-2.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guided_work_sessions",
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=True),
        sa.Column("workflow_key", sa.String(length=80), nullable=False),
        sa.Column("guidance_version", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("checklist_snapshot", sa.JSON(), nullable=False),
        sa.Column("completed_step_keys", sa.JSON(), nullable=False),
        sa.Column("baseline_minutes", sa.Numeric(10, 2), nullable=False),
        sa.Column("human_minutes", sa.Numeric(10, 2), nullable=True),
        sa.Column("outcome", sa.String(length=40), nullable=True),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("completed_by", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("pilot_log_entry_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "workflow_key = 'weekly_portfolio_review'",
            name="ck_guided_work_workflow_key",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'completed', 'cancelled')",
            name="ck_guided_work_status",
        ),
        sa.CheckConstraint(
            "baseline_minutes > 0",
            name="ck_guided_work_positive_baseline",
        ),
        sa.CheckConstraint(
            "human_minutes IS NULL OR (human_minutes >= 0 AND human_minutes <= 480)",
            name="ck_guided_work_human_minutes",
        ),
        sa.CheckConstraint(
            "(status = 'open' AND human_minutes IS NULL AND completed_by IS NULL "
            "AND completed_at IS NULL AND pilot_log_entry_id IS NULL "
            "AND cancelled_by IS NULL AND cancelled_at IS NULL) OR "
            "(status = 'completed' AND human_minutes IS NOT NULL "
            "AND completed_by IS NOT NULL AND completed_at IS NOT NULL "
            "AND pilot_log_entry_id IS NOT NULL AND cancelled_by IS NULL "
            "AND cancelled_at IS NULL) OR "
            "(status = 'cancelled' AND human_minutes IS NULL "
            "AND completed_by IS NULL AND completed_at IS NULL "
            "AND pilot_log_entry_id IS NULL AND cancelled_by IS NOT NULL "
            "AND cancelled_at IS NOT NULL)",
            name="ck_guided_work_state",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["started_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["pilot_log_entry_id"], ["pilot_log_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_guided_work_idempotency_key"),
        sa.UniqueConstraint("pilot_log_entry_id"),
    )
    op.create_index(
        "ix_guided_work_sessions_client_id",
        "guided_work_sessions",
        ["client_id"],
        unique=False,
    )
    op.create_index(
        "ix_guided_work_sessions_invoice_id",
        "guided_work_sessions",
        ["invoice_id"],
        unique=False,
    )
    op.create_index(
        "ix_guided_work_sessions_started_by",
        "guided_work_sessions",
        ["started_by"],
        unique=False,
    )
    op.create_index(
        "ix_guided_work_sessions_completed_by",
        "guided_work_sessions",
        ["completed_by"],
        unique=False,
    )
    op.create_index(
        "ix_guided_work_sessions_cancelled_by",
        "guided_work_sessions",
        ["cancelled_by"],
        unique=False,
    )
    op.create_index(
        "ix_guided_work_client_status_created",
        "guided_work_sessions",
        ["client_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_guided_work_client_status_created",
        table_name="guided_work_sessions",
    )
    op.drop_index("ix_guided_work_sessions_cancelled_by", table_name="guided_work_sessions")
    op.drop_index("ix_guided_work_sessions_completed_by", table_name="guided_work_sessions")
    op.drop_index("ix_guided_work_sessions_started_by", table_name="guided_work_sessions")
    op.drop_index("ix_guided_work_sessions_invoice_id", table_name="guided_work_sessions")
    op.drop_index("ix_guided_work_sessions_client_id", table_name="guided_work_sessions")
    op.drop_table("guided_work_sessions")
