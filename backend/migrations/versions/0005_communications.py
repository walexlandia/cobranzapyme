"""Add versioned communication templates and simulated outbox.

Revision ID: 0005
Revises: 0004
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "message_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("template_key", sa.String(80), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("stage", sa.String(40), nullable=False),
        sa.Column("recipient_role", sa.String(80), nullable=False),
        sa.Column("tone", sa.String(20), nullable=False),
        sa.Column("subject_template", sa.Text()),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("approved", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "client_id", "template_key", "channel", "version",
            name="uq_message_template_version",
        ),
    )
    op.create_index("ix_message_templates_client_id", "message_templates", ["client_id"])
    op.create_index(
        "uq_message_template_active",
        "message_templates",
        ["client_id", "template_key", "channel"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.create_table(
        "communication_threads",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("payer_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid()),
        sa.Column("channel", sa.String(30), nullable=False),
        sa.Column("external_thread_key", sa.String(255)),
        sa.Column("status", sa.String(30), server_default="open", nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"]),
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_communication_threads_client_id", "communication_threads", ["client_id"])
    op.create_index("ix_communication_threads_payer_id", "communication_threads", ["payer_id"])
    op.create_index("ix_communication_threads_contact_id", "communication_threads", ["contact_id"])
    op.create_index(
        "ix_communication_thread_participants",
        "communication_threads",
        ["client_id", "payer_id", "contact_id", "channel"],
    )

    op.add_column("messages", sa.Column("payer_id", sa.Uuid()))
    op.add_column("messages", sa.Column("contact_id", sa.Uuid()))
    op.add_column("messages", sa.Column("thread_id", sa.Uuid()))
    op.add_column("messages", sa.Column("template_id", sa.Uuid()))
    op.add_column("messages", sa.Column("workflow_job_id", sa.Uuid()))
    op.add_column("messages", sa.Column("subject", sa.Text()))
    op.add_column(
        "messages", sa.Column("status", sa.String(30), server_default="draft", nullable=False)
    )
    op.add_column("messages", sa.Column("idempotency_key", sa.String(255)))
    op.add_column(
        "messages",
        sa.Column(
            "provider_payload", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False
        ),
    )
    op.add_column(
        "messages",
        sa.Column("safety_status", sa.String(30), server_default="safe", nullable=False),
    )
    op.add_column(
        "messages",
        sa.Column(
            "safety_flags", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False
        ),
    )
    op.add_column(
        "messages", sa.Column("llm_cost", sa.Numeric(14, 6), server_default="0", nullable=False)
    )
    op.add_column(
        "messages",
        sa.Column("messaging_cost", sa.Numeric(14, 6), server_default="0", nullable=False),
    )
    op.add_column(
        "messages", sa.Column("cost_currency", sa.String(3), server_default="USD", nullable=False)
    )
    op.add_column("messages", sa.Column("sent_at", sa.DateTime(timezone=True)))
    op.add_column("messages", sa.Column("received_at", sa.DateTime(timezone=True)))
    op.create_foreign_key("fk_messages_payer", "messages", "payers", ["payer_id"], ["id"])
    op.create_foreign_key("fk_messages_contact", "messages", "contacts", ["contact_id"], ["id"])
    op.create_foreign_key(
        "fk_messages_thread", "messages", "communication_threads", ["thread_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_messages_template", "messages", "message_templates", ["template_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_messages_workflow_job", "messages", "workflow_jobs", ["workflow_job_id"], ["id"]
    )
    op.create_unique_constraint("uq_message_idempotency_key", "messages", ["idempotency_key"])
    op.create_index("ix_messages_payer_id", "messages", ["payer_id"])
    op.create_index("ix_messages_contact_id", "messages", ["contact_id"])
    op.create_index("ix_messages_thread_id", "messages", ["thread_id"])
    op.create_index("ix_messages_template_id", "messages", ["template_id"])
    op.create_index("ix_messages_workflow_job_id", "messages", ["workflow_job_id"])
    op.create_index("ix_message_outbox", "messages", ["client_id", "status", "created_at"])

    op.create_table(
        "message_invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("allocated_llm_cost", sa.Numeric(14, 6), server_default="0", nullable=False),
        sa.Column(
            "allocated_messaging_cost", sa.Numeric(14, 6), server_default="0", nullable=False
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "invoice_id", name="uq_message_invoice"),
    )
    op.create_index("ix_message_invoices_client_id", "message_invoices", ["client_id"])
    op.create_index("ix_message_invoices_message_id", "message_invoices", ["message_id"])
    op.create_index("ix_message_invoices_invoice_id", "message_invoices", ["invoice_id"])

    op.create_table(
        "message_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        *timestamps(),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "document_id", name="uq_message_document"),
    )
    op.create_index("ix_message_documents_client_id", "message_documents", ["client_id"])
    op.create_index("ix_message_documents_message_id", "message_documents", ["message_id"])
    op.create_index("ix_message_documents_document_id", "message_documents", ["document_id"])


def downgrade() -> None:
    op.drop_table("message_documents")
    op.drop_table("message_invoices")
    op.drop_index("ix_message_outbox", table_name="messages")
    op.drop_index("ix_messages_workflow_job_id", table_name="messages")
    op.drop_index("ix_messages_template_id", table_name="messages")
    op.drop_index("ix_messages_thread_id", table_name="messages")
    op.drop_index("ix_messages_contact_id", table_name="messages")
    op.drop_index("ix_messages_payer_id", table_name="messages")
    op.drop_constraint("uq_message_idempotency_key", "messages", type_="unique")
    op.drop_constraint("fk_messages_workflow_job", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_template", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_thread", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_contact", "messages", type_="foreignkey")
    op.drop_constraint("fk_messages_payer", "messages", type_="foreignkey")
    for column in [
        "received_at",
        "sent_at",
        "cost_currency",
        "messaging_cost",
        "llm_cost",
        "safety_flags",
        "safety_status",
        "provider_payload",
        "idempotency_key",
        "status",
        "subject",
        "workflow_job_id",
        "template_id",
        "thread_id",
        "contact_id",
        "payer_id",
    ]:
        op.drop_column("messages", column)
    op.drop_table("communication_threads")
    op.drop_table("message_templates")
