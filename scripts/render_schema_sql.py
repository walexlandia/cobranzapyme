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
"""
    )


if __name__ == "__main__":
    main()

