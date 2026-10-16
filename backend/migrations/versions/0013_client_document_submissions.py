"""Add supervised client document submissions.

Revision ID: 0013
Revises: 0012
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "client_document_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("payability_item_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected')",
            name="ck_client_document_submission_status",
        ),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.ForeignKeyConstraint(["payability_item_id"], ["payability_items.id"]),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", name="uq_client_document_submissions_document_id"),
        sa.UniqueConstraint(
            "client_id",
            "payability_item_id",
            "content_sha256",
            name="uq_client_document_submission_content",
        ),
    )
    for column in [
        "client_id",
        "invoice_id",
        "payability_item_id",
        "submitted_by",
        "reviewed_by",
    ]:
        op.create_index(
            f"ix_client_document_submissions_{column}",
            "client_document_submissions",
            [column],
        )
    op.create_index(
        "ix_client_document_submission_queue",
        "client_document_submissions",
        ["client_id", "status", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("client_document_submissions")
