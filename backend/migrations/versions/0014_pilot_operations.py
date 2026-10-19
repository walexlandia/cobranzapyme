"""Add the pilot operations log.

Revision ID: 0014
Revises: 0013
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilot_log_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("related_invoice_id", sa.Uuid()),
        sa.Column("entry_type", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), server_default="info", nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("human_minutes", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("resolved_by", sa.Uuid()),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "entry_type IN ('decision', 'incident', 'manual_work', 'rule_change', 'learning')",
            name="ck_pilot_log_entry_type",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="ck_pilot_log_severity",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'resolved')",
            name="ck_pilot_log_status",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["related_invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["client_id", "related_invoice_id", "created_by", "resolved_by"]:
        op.create_index(
            f"ix_pilot_log_entries_{column}",
            "pilot_log_entries",
            [column],
        )
    op.create_index(
        "ix_pilot_log_client_status_occurred",
        "pilot_log_entries",
        ["client_id", "status", "occurred_on"],
    )


def downgrade() -> None:
    op.drop_table("pilot_log_entries")
