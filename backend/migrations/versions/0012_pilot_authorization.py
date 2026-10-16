"""Add immutable pilot authorization ledger.

Revision ID: 0012
Revises: 0011
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilot_authorization_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("channels", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("authorized_contact_name", sa.String(200), nullable=False),
        sa.Column("authorized_contact_email", sa.String(320), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_until", sa.Date()),
        sa.Column("evidence_document_id", sa.Uuid()),
        sa.Column("supersedes_id", sa.Uuid()),
        sa.Column("performed_by", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("action IN ('approved', 'revoked')", name="ck_pilot_authorization_action"),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.ForeignKeyConstraint(["evidence_document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["pilot_authorization_events.id"]),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_pilot_authorization_idempotency"),
    )
    for column in ["client_id", "contract_id", "performed_by"]:
        op.create_index(
            f"ix_pilot_authorization_events_{column}",
            "pilot_authorization_events",
            [column],
        )
    op.create_index(
        "ix_pilot_authorization_client_created",
        "pilot_authorization_events",
        ["client_id", "created_at"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_pilot_authorization_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'pilot authorization events are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER pilot_authorization_events_are_immutable
        BEFORE UPDATE OR DELETE ON pilot_authorization_events
        FOR EACH ROW EXECUTE FUNCTION reject_pilot_authorization_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER pilot_authorization_events_are_immutable ON pilot_authorization_events")
    op.execute("DROP FUNCTION reject_pilot_authorization_mutation()")
    op.drop_table("pilot_authorization_events")
