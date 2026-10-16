"""Add immutable payment attribution and commission ledger.

Revision ID: 0009
Revises: 0008
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "payment_attributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("contract_id", sa.Uuid()),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("percentage", sa.Numeric(7, 4), nullable=False),
        sa.Column("base_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("rationale", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("calculated_by", sa.String(40), server_default="rules_v1", nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", name="uq_payment_attribution_payment"),
        sa.CheckConstraint("percentage >= 0 AND percentage <= 100", name="ck_attribution_percentage"),
        sa.CheckConstraint("base_amount > 0", name="ck_attribution_positive_base"),
        sa.CheckConstraint("commission_amount >= 0", name="ck_attribution_nonnegative_commission"),
    )
    for column in ["client_id", "payment_id", "invoice_id", "contract_id"]:
        op.create_index(
            f"ix_payment_attributions_{column}", "payment_attributions", [column]
        )
    op.execute(
        """
        CREATE FUNCTION reject_payment_attribution_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'payment attributions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER payment_attributions_are_immutable
        BEFORE UPDATE OR DELETE ON payment_attributions
        FOR EACH ROW EXECUTE FUNCTION reject_payment_attribution_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER payment_attributions_are_immutable ON payment_attributions")
    op.execute("DROP FUNCTION reject_payment_attribution_mutation()")
    op.drop_table("payment_attributions")
