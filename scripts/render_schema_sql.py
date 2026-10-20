"""Render the SQLAlchemy schema as PostgreSQL DDL for offline validation."""

import sys
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.base import Base  # noqa: E402
from app import models  # noqa: E402,F401


def main() -> None:
    dialect = postgresql.dialect()
    print("CREATE TYPE user_role AS ENUM ('ADMIN', 'OPERATOR', 'CLIENT');")
    print("CREATE TYPE invoice_status AS ENUM ('ISSUED', 'PAID', 'VOID', 'CLAIMED', 'DISPUTED');")
    print("CREATE TYPE actor_type AS ENUM ('SYSTEM', 'AI', 'HUMAN', 'PAYER');")
    for table in Base.metadata.sorted_tables:
        print(f"{CreateTable(table).compile(dialect=dialect)};")
    for table in Base.metadata.sorted_tables:
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            print(f"{CreateIndex(index).compile(dialect=dialect)};")
    print(
        """
CREATE FUNCTION reject_event_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'events are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER events_are_immutable
BEFORE UPDATE OR DELETE ON events
FOR EACH ROW EXECUTE FUNCTION reject_event_mutation();

CREATE FUNCTION reject_payer_profile_revision_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'payer profile revisions are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER payer_profile_revisions_are_immutable
BEFORE UPDATE OR DELETE ON payer_profile_revisions
FOR EACH ROW EXECUTE FUNCTION reject_payer_profile_revision_mutation();

CREATE FUNCTION reject_message_classification_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'message classifications are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER message_classifications_are_immutable
BEFORE UPDATE OR DELETE ON message_classifications
FOR EACH ROW EXECUTE FUNCTION reject_message_classification_mutation();

CREATE FUNCTION reject_evaluation_example_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'evaluation examples are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER evaluation_examples_are_immutable
BEFORE UPDATE OR DELETE ON evaluation_examples
FOR EACH ROW EXECUTE FUNCTION reject_evaluation_example_mutation();

CREATE FUNCTION reject_payment_attribution_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'payment attributions are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER payment_attributions_are_immutable
BEFORE UPDATE OR DELETE ON payment_attributions
FOR EACH ROW EXECUTE FUNCTION reject_payment_attribution_mutation();

CREATE FUNCTION reject_data_access_log_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'data access logs are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER data_access_logs_are_immutable
BEFORE UPDATE OR DELETE ON data_access_logs
FOR EACH ROW EXECUTE FUNCTION reject_data_access_log_mutation();

CREATE FUNCTION reject_pilot_authorization_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'pilot authorization events are immutable';
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER pilot_authorization_events_are_immutable
BEFORE UPDATE OR DELETE ON pilot_authorization_events
FOR EACH ROW EXECUTE FUNCTION reject_pilot_authorization_mutation();

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


if __name__ == "__main__":
    main()

