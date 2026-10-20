BEGIN;

INSERT INTO users (id, email, full_name, password_hash, role, active)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        'preparer@example.test', 'Preparador', 'test', 'OPERATOR', true
    ),
    (
        '22222222-2222-2222-2222-222222222222',
        'decider@example.test', 'Decisor', 'test', 'ADMIN', true
    );

INSERT INTO pilot_closure_snapshots (
    id,
    report_fingerprint,
    report_schema_version,
    evidence_kind,
    date_from,
    date_to,
    status,
    recommendation,
    report_data,
    economics_scenarios,
    backlog_priorities,
    prepared_by
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    repeat('a', 64),
    'fase-8.2-v1',
    'authorized_pilot',
    DATE '2026-01-01',
    DATE '2026-02-28',
    'prepared',
    'iterate',
    '{"g4":{"ready":true}}'::json,
    '[]'::json,
    '[]'::json,
    '11111111-1111-1111-1111-111111111111'
);

DO $$
BEGIN
    BEGIN
        UPDATE pilot_closure_snapshots
        SET report_data = '{"tampered":true}'::json
        WHERE id = '33333333-3333-3333-3333-333333333333';
        RAISE EXCEPTION 'tampering unexpectedly succeeded';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'pilot closure report evidence is immutable' THEN
                RAISE;
            END IF;
    END;

    BEGIN
        UPDATE pilot_closure_snapshots
        SET status = 'decided',
            decision = 'iterate',
            decided_by = prepared_by,
            decided_at = now(),
            decision_rationale = 'Intento de autoaprobación del mismo preparador.'
        WHERE id = '33333333-3333-3333-3333-333333333333';
        RAISE EXCEPTION 'self approval unexpectedly succeeded';
    EXCEPTION
        WHEN check_violation THEN
            NULL;
    END;

    UPDATE pilot_closure_snapshots
    SET status = 'decided',
        decision = 'iterate',
        decided_by = '22222222-2222-2222-2222-222222222222',
        decided_at = now(),
        decision_rationale = 'Iteración acotada validada por una segunda persona.'
    WHERE id = '33333333-3333-3333-3333-333333333333';

    BEGIN
        UPDATE pilot_closure_snapshots
        SET decision_rationale = 'Intento de reemplazo'
        WHERE id = '33333333-3333-3333-3333-333333333333';
        RAISE EXCEPTION 'second decision unexpectedly succeeded';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'decided pilot closure snapshots are immutable' THEN
                RAISE;
            END IF;
    END;

    BEGIN
        DELETE FROM pilot_closure_snapshots
        WHERE id = '33333333-3333-3333-3333-333333333333';
        RAISE EXCEPTION 'snapshot deletion unexpectedly succeeded';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'pilot closure snapshots cannot be deleted' THEN
                RAISE;
            END IF;
    END;
END;
$$;

ROLLBACK;
