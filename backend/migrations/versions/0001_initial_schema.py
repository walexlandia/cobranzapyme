"""Initial multi-tenant and audit schema.

Revision ID: 0001
Revises: None
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    user_role = postgresql.ENUM("ADMIN", "OPERATOR", "CLIENT", name="user_role")
    invoice_status = postgresql.ENUM(
        "ISSUED", "PAID", "VOID", "CLAIMED", "DISPUTED", name="invoice_status"
    )
    actor_type = postgresql.ENUM("SYSTEM", "AI", "HUMAN", "PAYER", name="actor_type")
    op.create_table(
        "clients",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("rut", sa.String(12), nullable=False),
        sa.Column("sender_name", sa.String(200)),
        sa.Column("sender_email", sa.String(320)),
        sa.Column("bank_details", sa.JSON(), nullable=False),
        sa.Column("baseline_dso", sa.Numeric(8, 2)),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rut"),
    )
    op.create_table(
        "payers",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("rut", sa.String(12), nullable=False),
        sa.Column("legal_name", sa.String(250), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rut"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("client_id", sa.Uuid()),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "version", name="uq_contract_client_version"),
    )
    op.create_table(
        "payer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("operational_requirements", sa.JSON(), nullable=False),
        sa.Column("supplier_portal_url", sa.String(500)),
        sa.Column("corporate_channels", sa.JSON(), nullable=False),
        sa.Column("payment_cycle", sa.String(200)),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payer_id"),
    )
    op.create_table(
        "client_payer_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("private_notes", sa.Text()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "payer_id", name="uq_client_payer"),
    )
    op.create_table(
        "contacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(80), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(40)),
        sa.Column("opted_out_email", sa.Boolean(), nullable=False),
        sa.Column("opted_out_whatsapp", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("folio", sa.String(80), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("purchase_order", sa.String(100)),
        sa.Column("status", invoice_status, nullable=False),
        sa.Column("source", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "document_type", "folio", name="uq_invoice_client_document"),
    )
    op.create_table(
        "payability_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("item_type", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("object_key", sa.String(500), nullable=False),
        sa.Column("original_name", sa.String(300), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("direction", sa.String(20), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("provider_id", sa.String(200)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("counterparty_rut", sa.String(12)),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "external_id", name="uq_bank_tx_client_external"),
    )
    op.create_table(
        "exception_cases",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid()),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("actor_type", actor_type, nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("paid_on", sa.Date(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("evidence_document_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["evidence_document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    indexed_columns = {
        "contracts": ["client_id"],
        "client_payer_relations": ["client_id", "payer_id"],
        "contacts": ["client_id", "payer_id"],
        "invoices": ["client_id", "payer_id"],
        "payability_items": ["client_id", "invoice_id"],
        "documents": ["client_id", "invoice_id"],
        "messages": ["client_id", "invoice_id"],
        "payments": ["client_id", "invoice_id"],
        "bank_transactions": ["client_id"],
        "exception_cases": ["client_id", "invoice_id"],
        "events": ["client_id", "invoice_id"],
    }
    for table, columns in indexed_columns.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_index("ix_contact_client_payer", "contacts", ["client_id", "payer_id"])
    op.create_index("ix_invoice_client_payer", "invoices", ["client_id", "payer_id"])
    op.create_index(
        "ix_event_client_invoice_created", "events", ["client_id", "invoice_id", "created_at"]
    )

    op.execute(
        """
        CREATE FUNCTION reject_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'events are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER events_are_immutable
        BEFORE UPDATE OR DELETE ON events
        FOR EACH ROW EXECUTE FUNCTION reject_event_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS events_are_immutable ON events")
    op.execute("DROP FUNCTION IF EXISTS reject_event_mutation()")
    for table in [
        "payments",
        "events",
        "exception_cases",
        "bank_transactions",
        "messages",
        "documents",
        "payability_items",
        "invoices",
        "contacts",
        "client_payer_relations",
        "payer_profiles",
        "contracts",
        "users",
        "payers",
        "clients",
    ]:
        op.drop_table(table)
    postgresql.ENUM(name="actor_type").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="invoice_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="user_role").drop(op.get_bind(), checkfirst=True)

