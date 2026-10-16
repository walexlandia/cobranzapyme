"""Track authenticated encryption for document bytes.

Revision ID: 0011
Revises: 0010
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("encryption_version", sa.String(30)))
    op.add_column("documents", sa.Column("encryption_nonce", sa.LargeBinary()))
    op.execute(
        "UPDATE documents SET encryption_version = 'legacy_plaintext' "
        "WHERE content IS NOT NULL AND encryption_version IS NULL"
    )
    op.create_check_constraint(
        "ck_document_encryption_metadata",
        "documents",
        "content IS NULL OR encryption_version = 'legacy_plaintext' OR "
        "(encryption_version = 'aesgcm-v1' AND encryption_nonce IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_document_encryption_metadata", "documents", type_="check")
    op.drop_column("documents", "encryption_nonce")
    op.drop_column("documents", "encryption_version")
