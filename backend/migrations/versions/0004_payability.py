"""Add payer profile history and invoice payability.

Revision ID: 0004
Revises: 0003
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.add_column("clients", sa.Column("baseline_on_time_percent", sa.Numeric(5, 2)))
    op.add_column(
        "clients",
        sa.Column("baseline_late_distribution", sa.JSON(), server_default="{}", nullable=False),
    )
    op.add_column("payer_profiles", sa.Column("supplier_portal_instructions", sa.Text()))

    op.add_column(
        "payability_items",
        sa.Column("label", sa.String(160), server_default="Requisito", nullable=False),
    )
    op.add_column(
        "payability_items",
        sa.Column("required", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "payability_items",
        sa.Column("blocks_payability", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.add_column(
        "payability_items",
        sa.Column("responsible_role", sa.String(80), server_default="client", nullable=False),
    )
    op.create_unique_constraint(
        "uq_payability_invoice_item", "payability_items", ["invoice_id", "item_type"]
    )

    op.create_table(
        "payer_profile_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payer_profile_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payer_profile_id"], ["payer_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "payer_profile_id", "version", name="uq_payer_profile_revision_version"
        ),
    )
    op.create_index(
        "ix_payer_profile_revisions_payer_profile_id",
        "payer_profile_revisions",
        ["payer_profile_id"],
    )
    op.execute(
        """
        CREATE FUNCTION reject_payer_profile_revision_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'payer profile revisions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER payer_profile_revisions_are_immutable
        BEFORE UPDATE OR DELETE ON payer_profile_revisions
        FOR EACH ROW EXECUTE FUNCTION reject_payer_profile_revision_mutation();
        """
    )

    op.create_table(
        "delay_causes",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("source", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_id"),
    )
    op.create_index("ix_delay_causes_client_id", "delay_causes", ["client_id"])
    op.create_index("ix_delay_causes_invoice_id", "delay_causes", ["invoice_id"])

    op.execute(
        """
        INSERT INTO payer_profiles (
            id, payer_id, operational_requirements, corporate_channels, payment_cycle
        )
        SELECT gen_random_uuid(), id,
               '{"requires_purchase_order":true,"requires_hes":false,"requires_delivery_note":false,"requires_supplier_portal":false,"other_requirements":[],"risk_days_before_due":7}'::json,
               '{}'::json, NULL
        FROM payers
        ON CONFLICT (payer_id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO payability_items (
            id, client_id, invoice_id, item_type, label, status, required,
            blocks_payability, responsible_role, evidence
        )
        SELECT gen_random_uuid(), client_id, id, 'sii_acceptance', 'Aceptación en SII',
               'pending', true, true, 'client', '{}'::json
        FROM invoices
        ON CONFLICT (invoice_id, item_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO payability_items (
            id, client_id, invoice_id, item_type, label, status, required,
            blocks_payability, responsible_role, evidence
        )
        SELECT gen_random_uuid(), client_id, id, 'purchase_order', 'Orden de compra',
               CASE WHEN purchase_order IS NULL THEN 'pending' ELSE 'fulfilled' END,
               true, true, 'client',
               CASE WHEN purchase_order IS NULL THEN '{}'::json
                    ELSE json_build_object('purchase_order', purchase_order) END
        FROM invoices
        ON CONFLICT (invoice_id, item_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO payability_items (
            id, client_id, invoice_id, item_type, label, status, required,
            blocks_payability, responsible_role, evidence
        )
        SELECT gen_random_uuid(), client_id, id, item_type, label, 'pending', false,
               false, 'accounts_payable', '{}'::json
        FROM invoices
        CROSS JOIN (VALUES
            ('payment_approval', 'Aprobación para pago'),
            ('payment_scheduled', 'Programación de pago')
        ) AS preventive(item_type, label)
        ON CONFLICT (invoice_id, item_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO events (
            id, client_id, invoice_id, event_type, actor_type, mode, payload
        )
        SELECT gen_random_uuid(), client_id, invoice_id, 'payability.item_created',
               'SYSTEM', 'automatic',
               json_build_object(
                   'item_type', item_type,
                   'label', label,
                   'status', status,
                   'required', required,
                   'responsible_role', responsible_role,
                   'source', 'migration_0004'
               )
        FROM payability_items
        """
    )


def downgrade() -> None:
    op.drop_table("delay_causes")
    op.execute(
        "DROP TRIGGER IF EXISTS payer_profile_revisions_are_immutable ON payer_profile_revisions"
    )
    op.execute("DROP FUNCTION IF EXISTS reject_payer_profile_revision_mutation()")
    op.drop_table("payer_profile_revisions")
    op.drop_constraint("uq_payability_invoice_item", "payability_items", type_="unique")
    op.drop_column("payability_items", "responsible_role")
    op.drop_column("payability_items", "blocks_payability")
    op.drop_column("payability_items", "required")
    op.drop_column("payability_items", "label")
    op.drop_column("clients", "baseline_late_distribution")
    op.drop_column("clients", "baseline_on_time_percent")
    op.drop_column("payer_profiles", "supplier_portal_instructions")
