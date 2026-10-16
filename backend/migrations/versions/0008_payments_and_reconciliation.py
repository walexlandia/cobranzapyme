"""Add supervised payment reconciliation.

Revision ID: 0008
Revises: 0007
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("documents", sa.Column("content", sa.LargeBinary()))

    op.add_column(
        "bank_transactions",
        sa.Column("currency", sa.String(3), server_default="CLP", nullable=False),
    )
    op.add_column(
        "bank_transactions",
        sa.Column("status", sa.String(30), server_default="unmatched", nullable=False),
    )
    op.add_column("bank_transactions", sa.Column("source_filename", sa.String(300)))
    op.add_column("bank_transactions", sa.Column("source_row", sa.Integer()))
    op.add_column(
        "bank_transactions",
        sa.Column("raw_data", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column("bank_transactions", sa.Column("imported_by", sa.Uuid()))
    op.create_foreign_key(
        "fk_bank_transaction_imported_by", "bank_transactions", "users", ["imported_by"], ["id"]
    )
    op.create_index(
        "ix_bank_transactions_imported_by", "bank_transactions", ["imported_by"]
    )

    op.add_column("payments", sa.Column("bank_transaction_id", sa.Uuid()))
    op.add_column(
        "payments", sa.Column("source", sa.String(30), server_default="manual", nullable=False)
    )
    op.add_column("payments", sa.Column("reference", sa.String(200)))
    op.add_column("payments", sa.Column("verified_by", sa.Uuid()))
    op.add_column("payments", sa.Column("verified_at", sa.DateTime(timezone=True)))
    op.add_column("payments", sa.Column("idempotency_key", sa.String(255)))
    op.create_foreign_key(
        "fk_payment_bank_transaction",
        "payments",
        "bank_transactions",
        ["bank_transaction_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_payment_verified_by", "payments", "users", ["verified_by"], ["id"]
    )
    op.create_index("ix_payments_bank_transaction_id", "payments", ["bank_transaction_id"])
    op.create_index("ix_payments_verified_by", "payments", ["verified_by"])
    op.create_unique_constraint("uq_payment_idempotency_key", "payments", ["idempotency_key"])
    op.create_unique_constraint(
        "uq_payment_bank_transaction_invoice",
        "payments",
        ["bank_transaction_id", "invoice_id"],
    )
    op.create_check_constraint("ck_payment_positive_amount", "payments", "amount > 0")

    op.create_table(
        "reconciliation_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("bank_transaction_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_key", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), server_default="pending", nullable=False),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column("score_breakdown", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["bank_transaction_id"], ["bank_transactions.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "bank_transaction_id", "candidate_key", name="uq_reconciliation_candidate"
        ),
    )
    for column in ["client_id", "bank_transaction_id", "reviewed_by"]:
        op.create_index(
            f"ix_reconciliation_proposals_{column}", "reconciliation_proposals", [column]
        )
    op.create_index(
        "uq_reconciliation_confirmed_transaction",
        "reconciliation_proposals",
        ["bank_transaction_id"],
        unique=True,
        postgresql_where=sa.text("status = 'confirmed'"),
    )

    op.create_table(
        "reconciliation_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(18, 2), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["reconciliation_proposals.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "invoice_id", name="uq_reconciliation_item_invoice"),
        sa.CheckConstraint("allocated_amount > 0", name="ck_reconciliation_positive_allocation"),
    )
    for column in ["client_id", "proposal_id", "invoice_id"]:
        op.create_index(
            f"ix_reconciliation_items_{column}", "reconciliation_items", [column]
        )


def downgrade() -> None:
    op.drop_table("reconciliation_items")
    op.drop_table("reconciliation_proposals")
    op.drop_constraint("ck_payment_positive_amount", "payments", type_="check")
    op.drop_constraint("uq_payment_bank_transaction_invoice", "payments", type_="unique")
    op.drop_constraint("uq_payment_idempotency_key", "payments", type_="unique")
    op.drop_index("ix_payments_verified_by", table_name="payments")
    op.drop_index("ix_payments_bank_transaction_id", table_name="payments")
    op.drop_constraint("fk_payment_verified_by", "payments", type_="foreignkey")
    op.drop_constraint("fk_payment_bank_transaction", "payments", type_="foreignkey")
    for column in [
        "idempotency_key",
        "verified_at",
        "verified_by",
        "reference",
        "source",
        "bank_transaction_id",
    ]:
        op.drop_column("payments", column)
    op.drop_index("ix_bank_transactions_imported_by", table_name="bank_transactions")
    op.drop_constraint("fk_bank_transaction_imported_by", "bank_transactions", type_="foreignkey")
    for column in [
        "imported_by",
        "raw_data",
        "source_row",
        "source_filename",
        "status",
        "currency",
    ]:
        op.drop_column("bank_transactions", column)
    op.drop_column("documents", "content")
