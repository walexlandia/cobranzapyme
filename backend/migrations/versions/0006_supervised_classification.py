"""Add immutable message classifications and an operational exception queue.

Revision ID: 0006
Revises: 0005
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "message_classifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("extracted_data", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("evidence", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("classifier_kind", sa.String(30), nullable=False),
        sa.Column("classifier_version", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(80)),
        sa.Column("decision_source", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("supersedes_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["message_classifications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "version", name="uq_message_classification_version"),
    )
    op.create_index(
        "ix_message_classifications_client_id", "message_classifications", ["client_id"]
    )
    op.create_index(
        "ix_message_classifications_message_id", "message_classifications", ["message_id"]
    )
    op.create_index(
        "ix_message_classifications_invoice_id", "message_classifications", ["invoice_id"]
    )
    op.create_index(
        "ix_message_classifications_supersedes_id",
        "message_classifications",
        ["supersedes_id"],
    )
    op.create_index(
        "ix_message_classification_history",
        "message_classifications",
        ["client_id", "message_id", "created_at"],
    )

    op.add_column("exception_cases", sa.Column("message_id", sa.Uuid()))
    op.add_column("exception_cases", sa.Column("classification_id", sa.Uuid()))
    op.add_column("exception_cases", sa.Column("assigned_to", sa.Uuid()))
    op.add_column(
        "exception_cases",
        sa.Column("human_minutes", sa.Numeric(10, 2), server_default="0", nullable=False),
    )
    op.add_column("exception_cases", sa.Column("resolved_at", sa.DateTime(timezone=True)))
    op.add_column(
        "exception_cases",
        sa.Column("resolution", sa.JSON(), server_default="{}", nullable=False),
    )
    op.create_foreign_key(
        "fk_exception_cases_message", "exception_cases", "messages", ["message_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_exception_cases_classification",
        "exception_cases",
        "message_classifications",
        ["classification_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_exception_cases_assigned_to", "exception_cases", "users", ["assigned_to"], ["id"]
    )
    op.create_index("ix_exception_cases_message_id", "exception_cases", ["message_id"])
    op.create_index(
        "ix_exception_cases_classification_id", "exception_cases", ["classification_id"]
    )
    op.create_index("ix_exception_cases_assigned_to", "exception_cases", ["assigned_to"])
    op.create_index(
        "ix_exception_queue",
        "exception_cases",
        ["client_id", "status", "priority", "created_at"],
    )
    op.create_index(
        "uq_exception_open_message",
        "exception_cases",
        ["message_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open' AND message_id IS NOT NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION reject_message_classification_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'message classifications are immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER message_classifications_are_immutable
        BEFORE UPDATE OR DELETE ON message_classifications
        FOR EACH ROW EXECUTE FUNCTION reject_message_classification_mutation();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS message_classifications_are_immutable "
        "ON message_classifications"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_message_classification_mutation()")
    op.drop_index("uq_exception_open_message", table_name="exception_cases")
    op.drop_index("ix_exception_queue", table_name="exception_cases")
    op.drop_index("ix_exception_cases_assigned_to", table_name="exception_cases")
    op.drop_index("ix_exception_cases_classification_id", table_name="exception_cases")
    op.drop_index("ix_exception_cases_message_id", table_name="exception_cases")
    op.drop_constraint("fk_exception_cases_assigned_to", "exception_cases", type_="foreignkey")
    op.drop_constraint(
        "fk_exception_cases_classification", "exception_cases", type_="foreignkey"
    )
    op.drop_constraint("fk_exception_cases_message", "exception_cases", type_="foreignkey")
    for column in [
        "resolution",
        "resolved_at",
        "human_minutes",
        "assigned_to",
        "classification_id",
        "message_id",
    ]:
        op.drop_column("exception_cases", column)
    op.drop_table("message_classifications")
