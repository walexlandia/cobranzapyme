"""Add workflow controls and grouped job recipients.

Revision ID: 0003
Revises: 0002
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "workflow_controls",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(200)),
        sa.Column("resume_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "scope_type", "scope_id", name="uq_workflow_control_scope"),
    )
    op.create_index("ix_workflow_controls_client_id", "workflow_controls", ["client_id"])
    op.create_index("ix_workflow_controls_scope_id", "workflow_controls", ["scope_id"])
    op.create_index("ix_workflow_controls_resume_at", "workflow_controls", ["resume_at"])

    op.add_column("workflow_jobs", sa.Column("payer_id", sa.Uuid(), nullable=True))
    op.add_column("workflow_jobs", sa.Column("recipient_contact_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_workflow_jobs_payer", "workflow_jobs", "payers", ["payer_id"], ["id"])
    op.create_foreign_key(
        "fk_workflow_jobs_recipient_contact",
        "workflow_jobs",
        "contacts",
        ["recipient_contact_id"],
        ["id"],
    )
    op.create_index("ix_workflow_jobs_payer_id", "workflow_jobs", ["payer_id"])
    op.create_index(
        "ix_workflow_jobs_recipient_contact_id", "workflow_jobs", ["recipient_contact_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_jobs_recipient_contact_id", table_name="workflow_jobs")
    op.drop_index("ix_workflow_jobs_payer_id", table_name="workflow_jobs")
    op.drop_constraint("fk_workflow_jobs_recipient_contact", "workflow_jobs", type_="foreignkey")
    op.drop_constraint("fk_workflow_jobs_payer", "workflow_jobs", type_="foreignkey")
    op.drop_column("workflow_jobs", "recipient_contact_id")
    op.drop_column("workflow_jobs", "payer_id")
    op.drop_table("workflow_controls")
