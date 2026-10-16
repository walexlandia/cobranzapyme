"""Add workflow state and idempotent job queue.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_index(
        "uq_contract_active_client",
        "contracts",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.create_table(
        "workflow_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("pause_reason", sa.String(120)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id", name="uq_workflow_state_invoice"),
    )
    op.create_index("ix_workflow_states_client_id", "workflow_states", ["client_id"])
    op.create_index("ix_workflow_states_invoice_id", "workflow_states", ["invoice_id"])
    op.create_index("ix_workflow_states_contract_id", "workflow_states", ["contract_id"])
    op.create_index("ix_workflow_states_next_run_at", "workflow_states", ["next_run_at"])

    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("action_type", sa.String(80), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_workflow_job_idempotency_key"),
    )
    op.create_index("ix_workflow_jobs_client_id", "workflow_jobs", ["client_id"])
    op.create_index("ix_workflow_jobs_invoice_id", "workflow_jobs", ["invoice_id"])
    op.create_index("ix_workflow_jobs_contract_id", "workflow_jobs", ["contract_id"])
    op.create_index("ix_workflow_job_due", "workflow_jobs", ["status", "scheduled_for"])


def downgrade() -> None:
    op.drop_table("workflow_jobs")
    op.drop_table("workflow_states")
    op.drop_index("uq_contract_active_client", table_name="contracts")
