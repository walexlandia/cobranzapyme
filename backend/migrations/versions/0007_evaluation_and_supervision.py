"""Add versioned evaluation, category policies and payer profile proposals.

Revision ID: 0007
Revises: 0006
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "evaluation_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.Column("anonymization_version", sa.String(80), nullable=False),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("metrics", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "version", name="uq_evaluation_set_version"),
    )
    op.create_index("ix_evaluation_sets_client_id", "evaluation_sets", ["client_id"])
    op.create_index(
        "uq_evaluation_set_open",
        "evaluation_sets",
        ["client_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    op.create_table(
        "evaluation_examples",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_set_id", sa.Uuid(), nullable=False),
        sa.Column("classification_id", sa.Uuid(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("redacted_text", sa.Text(), nullable=False),
        sa.Column("predicted_category", sa.String(80), nullable=False),
        sa.Column("actual_category", sa.String(80), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), server_default="{}", nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["evaluation_set_id"], ["evaluation_sets.id"]),
        sa.ForeignKeyConstraint(["classification_id"], ["message_classifications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("classification_id"),
        sa.UniqueConstraint(
            "evaluation_set_id", "source_hash", name="uq_evaluation_example_source"
        ),
    )
    op.create_index("ix_evaluation_examples_client_id", "evaluation_examples", ["client_id"])
    op.create_index(
        "ix_evaluation_examples_evaluation_set_id",
        "evaluation_examples",
        ["evaluation_set_id"],
    )
    op.create_index(
        "ix_evaluation_examples_classification_id",
        "evaluation_examples",
        ["classification_id"],
    )

    op.create_table(
        "classification_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("mode", sa.String(30), server_default="supervised", nullable=False),
        sa.Column("minimum_precision", sa.Numeric(5, 4), server_default="0.9000", nullable=False),
        sa.Column("minimum_samples", sa.Integer(), server_default="20", nullable=False),
        sa.Column("current_precision", sa.Numeric(5, 4)),
        sa.Column("sample_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("eligible_for_automation", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "category", name="uq_classification_policy_category"),
    )
    op.create_index(
        "ix_classification_policies_client_id", "classification_policies", ["client_id"]
    )

    op.create_table(
        "payer_profile_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("exception_id", sa.Uuid()),
        sa.Column("classification_id", sa.Uuid()),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("proposed_changes", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.ForeignKeyConstraint(["exception_id"], ["exception_cases.id"]),
        sa.ForeignKeyConstraint(["classification_id"], ["message_classifications.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ["client_id", "payer_id", "exception_id", "classification_id", "reviewed_by"]:
        op.create_index(
            f"ix_payer_profile_proposals_{column}", "payer_profile_proposals", [column]
        )

    op.execute(
        """
        CREATE FUNCTION reject_evaluation_example_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'evaluation examples are immutable';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER evaluation_examples_are_immutable
        BEFORE UPDATE OR DELETE ON evaluation_examples
        FOR EACH ROW EXECUTE FUNCTION reject_evaluation_example_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS evaluation_examples_are_immutable ON evaluation_examples")
    op.execute("DROP FUNCTION IF EXISTS reject_evaluation_example_mutation()")
    op.drop_table("payer_profile_proposals")
    op.drop_table("classification_policies")
    op.drop_table("evaluation_examples")
    op.drop_table("evaluation_sets")
