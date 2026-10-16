"""Add immutable authenticated data access logs.

Revision ID: 0010
Revises: 0009
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "data_access_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("actor_role", sa.String(30), nullable=False),
        sa.Column("client_id", sa.Uuid()),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("remote_hash", sa.String(64)),
        sa.Column("user_agent", sa.String(300)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index("ix_data_access_logs_user_id", "data_access_logs", ["user_id"])
    op.create_index("ix_data_access_logs_client_id", "data_access_logs", ["client_id"])
    op.create_index(
        "ix_data_access_client_created", "data_access_logs", ["client_id", "created_at"]
    )
    op.execute(
        """
        CREATE FUNCTION reject_data_access_log_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'data access logs are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER data_access_logs_are_immutable
        BEFORE UPDATE OR DELETE ON data_access_logs
        FOR EACH ROW EXECUTE FUNCTION reject_data_access_log_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER data_access_logs_are_immutable ON data_access_logs")
    op.execute("DROP FUNCTION reject_data_access_log_mutation()")
    op.drop_table("data_access_logs")
