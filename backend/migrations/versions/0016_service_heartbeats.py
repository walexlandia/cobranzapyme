"""Add cross-process service heartbeat state.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_heartbeats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(20), server_default="healthy", nullable=False),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_failure_at", sa.DateTime(timezone=True)),
        sa.Column(
            "consecutive_failures", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "last_cycle",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
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
            "status IN ('healthy', 'degraded')", name="ck_service_heartbeat_status"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_name", name="uq_service_heartbeat_name"),
    )


def downgrade() -> None:
    op.drop_table("service_heartbeats")
