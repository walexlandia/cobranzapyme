"""Add client industry for comparable cohort concentration.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("industry", sa.String(length=80), nullable=True))
    op.create_index("ix_clients_industry", "clients", ["industry"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clients_industry", table_name="clients")
    op.drop_column("clients", "industry")
