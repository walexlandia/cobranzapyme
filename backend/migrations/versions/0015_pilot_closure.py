"""Add immutable pilot closure snapshots and human G4 decisions.

Revision ID: 0015
Revises: 0014
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pilot_closure_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_fingerprint", sa.String(64), nullable=False),
        sa.Column("report_schema_version", sa.String(40), nullable=False),
        sa.Column("evidence_kind", sa.String(30), nullable=False),
        sa.Column("date_from", sa.Date(), nullable=False),
        sa.Column("date_to", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="prepared", nullable=False),
        sa.Column("recommendation", sa.String(20), nullable=False),
        sa.Column("decision", sa.String(20)),
        sa.Column("report_data", sa.JSON(), nullable=False),
        sa.Column("economics_scenarios", sa.JSON(), nullable=False),
        sa.Column("backlog_priorities", sa.JSON(), nullable=False),
        sa.Column("prepared_by", sa.Uuid(), nullable=False),
        sa.Column("decided_by", sa.Uuid()),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("decision_rationale", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "evidence_kind IN ('synthetic', 'authorized_pilot')",
            name="ck_pilot_closure_evidence_kind",
        ),
        sa.CheckConstraint(
            "status IN ('prepared', 'decided')",
            name="ck_pilot_closure_status",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('scale', 'iterate', 'pivot', 'stop')",
            name="ck_pilot_closure_decision",
        ),
        sa.CheckConstraint(
            "(status = 'prepared' AND decision IS NULL AND decided_by IS NULL "
            "AND decided_at IS NULL AND decision_rationale IS NULL) OR "
            "(status = 'decided' AND decision IS NOT NULL AND decided_by IS NOT NULL "
            "AND decided_by <> prepared_by AND decided_at IS NOT NULL "
            "AND decision_rationale IS NOT NULL)",
            name="ck_pilot_closure_decision_state",
        ),
        sa.ForeignKeyConstraint(["prepared_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "report_fingerprint",
            name="uq_pilot_closure_report_fingerprint",
        ),
    )
    op.create_index(
        "ix_pilot_closure_status_created",
        "pilot_closure_snapshots",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_pilot_closure_snapshots_prepared_by",
        "pilot_closure_snapshots",
        ["prepared_by"],
    )
    op.create_index(
        "ix_pilot_closure_snapshots_decided_by",
        "pilot_closure_snapshots",
        ["decided_by"],
    )
    op.execute(
        """
        CREATE FUNCTION protect_pilot_closure_snapshot() RETURNS trigger AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION 'pilot closure snapshots cannot be deleted';
            END IF;
            IF OLD.status = 'decided' THEN
                RAISE EXCEPTION 'decided pilot closure snapshots are immutable';
            END IF;
            IF NEW.report_fingerprint IS DISTINCT FROM OLD.report_fingerprint
                OR NEW.report_schema_version IS DISTINCT FROM OLD.report_schema_version
                OR NEW.evidence_kind IS DISTINCT FROM OLD.evidence_kind
                OR NEW.date_from IS DISTINCT FROM OLD.date_from
                OR NEW.date_to IS DISTINCT FROM OLD.date_to
                OR NEW.recommendation IS DISTINCT FROM OLD.recommendation
                OR NEW.report_data::jsonb IS DISTINCT FROM OLD.report_data::jsonb
                OR NEW.economics_scenarios::jsonb IS DISTINCT FROM OLD.economics_scenarios::jsonb
                OR NEW.backlog_priorities::jsonb IS DISTINCT FROM OLD.backlog_priorities::jsonb
                OR NEW.prepared_by IS DISTINCT FROM OLD.prepared_by
                OR NEW.created_at IS DISTINCT FROM OLD.created_at
            THEN
                RAISE EXCEPTION 'pilot closure report evidence is immutable';
            END IF;
            IF NEW.status <> 'decided' THEN
                RAISE EXCEPTION 'the only allowed update is the final G4 decision';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER pilot_closure_snapshots_are_immutable
        BEFORE UPDATE OR DELETE ON pilot_closure_snapshots
        FOR EACH ROW EXECUTE FUNCTION protect_pilot_closure_snapshot();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS pilot_closure_snapshots_are_immutable "
        "ON pilot_closure_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS protect_pilot_closure_snapshot()")
    op.drop_table("pilot_closure_snapshots")
