\set ON_ERROR_STOP on

INSERT INTO clients (
    id, name, rut, bank_details, active
) VALUES (
    '10000000-0000-0000-0000-000000000001',
    'Pyme de prueba',
    'TEST-1',
    '{}'::json,
    true
);

INSERT INTO payers (
    id, rut, legal_name
) VALUES (
    '20000000-0000-0000-0000-000000000001',
    'TEST-PAYER',
    'Pagador de prueba'
);

INSERT INTO invoices (
    id, client_id, payer_id, document_type, folio, issued_on, due_on,
    currency, total_amount, status, source
) VALUES (
    '30000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    'factura', 'F-1', DATE '2026-10-01', DATE '2026-10-31',
    'CLP', 100000, 'ISSUED', 'test'
);

INSERT INTO events (
    id, client_id, invoice_id, event_type, actor_type, mode, payload
) VALUES (
    '40000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    'invoice.created', 'SYSTEM', 'automatic', '{}'::json
);

DO $$
BEGIN
    BEGIN
        UPDATE events SET event_type = 'tampered'
        WHERE id = '40000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'immutability check failed: update was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'events are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO payer_profiles (
    id, payer_id, operational_requirements, corporate_channels
) VALUES (
    '65000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '{"requires_purchase_order":true}'::json,
    '{}'::json
);

INSERT INTO payer_profile_revisions (
    id, payer_profile_id, version, snapshot
) VALUES (
    '66000000-0000-0000-0000-000000000001',
    '65000000-0000-0000-0000-000000000001',
    1,
    '{"payment_cycle":"viernes"}'::json
);

DO $$
BEGIN
    BEGIN
        UPDATE payer_profile_revisions SET version = 2
        WHERE id = '66000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'payer profile revision immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'payer profile revisions are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO payability_items (
    id, client_id, invoice_id, item_type, label, status, required,
    blocks_payability, responsible_role, evidence
) VALUES (
    '67000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    'sii_acceptance', 'Aceptación SII', 'pending', true, true, 'client', '{}'::json
);

DO $$
BEGIN
    BEGIN
        INSERT INTO payability_items (
            id, client_id, invoice_id, item_type, label, status, required,
            blocks_payability, responsible_role, evidence
        ) VALUES (
            '67000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            'sii_acceptance', 'Aceptación SII', 'fulfilled', true, true, 'client', '{}'::json
        );
        RAISE EXCEPTION 'payability duplicate item check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        DELETE FROM events
        WHERE id = '40000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'immutability check failed: delete was accepted';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'events are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO invoices (
            id, client_id, payer_id, document_type, folio, issued_on, due_on,
            currency, total_amount, status, source
        ) VALUES (
            '30000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '20000000-0000-0000-0000-000000000001',
            'factura', 'F-1', DATE '2026-10-01', DATE '2026-10-31',
            'CLP', 100000, 'ISSUED', 'test'
        );
        RAISE EXCEPTION 'duplicate check failed: duplicate invoice was accepted';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO contracts (
    id, client_id, version, rules, active
) VALUES (
    '50000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    1,
    '{"timezone":"America/Santiago"}'::json,
    true
);

DO $$
BEGIN
    BEGIN
        INSERT INTO contracts (
            id, client_id, version, rules, active
        ) VALUES (
            '50000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            2,
            '{"timezone":"America/Santiago"}'::json,
            true
        );
        RAISE EXCEPTION 'active contract check failed: two active versions were accepted';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO workflow_controls (
    id, client_id, scope_type, scope_id, status, reason
) VALUES (
    '55000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'invoice',
    '30000000-0000-0000-0000-000000000001',
    'paused',
    'operator_review'
);

DO $$
BEGIN
    BEGIN
        INSERT INTO workflow_controls (
            id, client_id, scope_type, scope_id, status
        ) VALUES (
            '55000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            'invoice',
            '30000000-0000-0000-0000-000000000001',
            'active'
        );
        RAISE EXCEPTION 'workflow control check failed: duplicate scope was accepted';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO workflow_jobs (
    id, client_id, invoice_id, payer_id, contract_id, idempotency_key, action_type,
    stage, status, scheduled_for, attempts, mode, payload
) VALUES (
    '60000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000001',
    'invoice-contract-stage-date',
    'resolve_payability',
    'documental',
    'pending',
    TIMESTAMPTZ '2026-10-14 12:00:00+00',
    0,
    'automatic',
    '{}'::json
);

DO $$
BEGIN
    BEGIN
        INSERT INTO workflow_jobs (
            id, client_id, invoice_id, payer_id, contract_id, idempotency_key, action_type,
            stage, status, scheduled_for, attempts, mode, payload
        ) VALUES (
            '60000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            '20000000-0000-0000-0000-000000000001',
            '50000000-0000-0000-0000-000000000001',
            'invoice-contract-stage-date',
            'resolve_payability',
            'documental',
            'pending',
            TIMESTAMPTZ '2026-10-14 12:00:00+00',
            0,
            'manual',
            '{}'::json
        );
        RAISE EXCEPTION 'idempotency check failed: duplicate workflow job was accepted';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO contacts (
    id, client_id, payer_id, name, role, email, phone,
    opted_out_email, opted_out_whatsapp
) VALUES (
    '70000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    'Contacto CxP', 'accounts_payable', 'cxp@example.test', '+56911111111',
    false, false
);

INSERT INTO message_templates (
    id, client_id, template_key, version, channel, stage, recipient_role,
    tone, subject_template, body_template, approved, active
) VALUES (
    '71000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'payment_due', 1, 'email', 'due', 'accounts_payable',
    'cordial', 'Seguimiento', 'Mensaje seguro', false, true
);

DO $$
BEGIN
    BEGIN
        INSERT INTO message_templates (
            id, client_id, template_key, version, channel, stage, recipient_role,
            tone, body_template, approved, active
        ) VALUES (
            '71000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            'payment_due', 1, 'email', 'due', 'accounts_payable',
            'cordial', 'Duplicada', false, false
        );
        RAISE EXCEPTION 'message template version check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO communication_threads (
    id, client_id, payer_id, contact_id, channel, status
) VALUES (
    '72000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '70000000-0000-0000-0000-000000000001',
    'email', 'open'
);

INSERT INTO messages (
    id, client_id, invoice_id, payer_id, contact_id, thread_id, template_id,
    workflow_job_id, channel, direction, mode, subject, body, status,
    idempotency_key, provider_payload, safety_status, safety_flags,
    llm_cost, messaging_cost, cost_currency
) VALUES (
    '73000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '70000000-0000-0000-0000-000000000001',
    '72000000-0000-0000-0000-000000000001',
    '71000000-0000-0000-0000-000000000001',
    '60000000-0000-0000-0000-000000000001',
    'email', 'outbound', 'automatic', 'Seguimiento', 'Mensaje seguro', 'draft',
    'workflow:test:outbound:v1', '{}'::json, 'safe', '[]'::json,
    0, 0, 'USD'
);

INSERT INTO message_invoices (
    id, client_id, message_id, invoice_id,
    allocated_llm_cost, allocated_messaging_cost
) VALUES (
    '74000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '73000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    0, 0
);

DO $$
BEGIN
    BEGIN
        INSERT INTO messages (
            id, client_id, channel, direction, mode, body, status,
            idempotency_key, provider_payload, safety_status, safety_flags,
            llm_cost, messaging_cost, cost_currency
        ) VALUES (
            '73000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            'email', 'outbound', 'manual', 'Duplicado', 'draft',
            'workflow:test:outbound:v1', '{}'::json, 'safe', '[]'::json,
            0, 0, 'USD'
        );
        RAISE EXCEPTION 'message idempotency check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO message_invoices (
            id, client_id, message_id, invoice_id,
            allocated_llm_cost, allocated_messaging_cost
        ) VALUES (
            '74000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '73000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            0, 0
        );
        RAISE EXCEPTION 'message invoice uniqueness check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO message_classifications (
    id, client_id, message_id, invoice_id, version, category, confidence,
    extracted_data, evidence, classifier_kind, classifier_version,
    decision_source
) VALUES (
    '75000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '73000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    1, 'payment_scheduled', 0.94,
    '{"payment_dates":["2026-10-24"]}'::json,
    '{"matched_phrases":{"payment_scheduled":["pago programado"]}}'::json,
    'rule_based', 'local-rules-v1', 'system'
);

DO $$
BEGIN
    BEGIN
        UPDATE message_classifications SET category = 'paid'
        WHERE id = '75000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'classification immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'message classifications are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO exception_cases (
    id, client_id, invoice_id, message_id, classification_id,
    kind, status, priority, detail, human_minutes, resolution
) VALUES (
    '76000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '73000000-0000-0000-0000-000000000001',
    '75000000-0000-0000-0000-000000000001',
    'supervised_review', 'open', 50, '{}'::json, 0, '{}'::json
);

DO $$
BEGIN
    BEGIN
        INSERT INTO exception_cases (
            id, client_id, invoice_id, message_id, classification_id,
            kind, status, priority, detail, human_minutes, resolution
        ) VALUES (
            '76000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            '73000000-0000-0000-0000-000000000001',
            '75000000-0000-0000-0000-000000000001',
            'supervised_review', 'open', 40, '{}'::json, 0, '{}'::json
        );
        RAISE EXCEPTION 'open exception uniqueness check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO evaluation_sets (
    id, client_id, version, status, anonymization_version, sample_count, metrics
) VALUES (
    '77000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    1, 'open', 'local-redaction-v1', 1, '{}'::json
);

DO $$
BEGIN
    BEGIN
        INSERT INTO evaluation_sets (
            id, client_id, version, status, anonymization_version, sample_count, metrics
        ) VALUES (
            '77000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            2, 'open', 'local-redaction-v1', 0, '{}'::json
        );
        RAISE EXCEPTION 'open evaluation set uniqueness check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO evaluation_examples (
    id, client_id, evaluation_set_id, classification_id, source_hash,
    redacted_text, predicted_category, actual_category, correct, metadata_json
) VALUES (
    '78000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '77000000-0000-0000-0000-000000000001',
    '75000000-0000-0000-0000-000000000001',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'Pago programado para [FECHA].',
    'payment_scheduled', 'payment_scheduled', TRUE, '{}'::json
);

DO $$
BEGIN
    BEGIN
        UPDATE evaluation_examples SET actual_category = 'paid'
        WHERE id = '78000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'evaluation example immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'evaluation examples are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO classification_policies (
    id, client_id, category, mode, minimum_precision, minimum_samples,
    current_precision, sample_count, eligible_for_automation
) VALUES (
    '79000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'payment_scheduled', 'supervised', 0.9000, 20, 1.0000, 1, FALSE
);

DO $$
BEGIN
    BEGIN
        INSERT INTO classification_policies (
            id, client_id, category, mode, minimum_precision, minimum_samples,
            sample_count, eligible_for_automation
        ) VALUES (
            '79000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            'payment_scheduled', 'supervised', 0.9000, 20, 0, FALSE
        );
        RAISE EXCEPTION 'classification policy uniqueness check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO payer_profile_proposals (
    id, client_id, payer_id, exception_id, classification_id,
    status, proposed_changes, rationale
) VALUES (
    '7a000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '76000000-0000-0000-0000-000000000001',
    '75000000-0000-0000-0000-000000000001',
    'pending', '{"payment_cycle":"Días 10 y 25"}'::json,
    'Patrón observado durante la revisión supervisada.'
);

INSERT INTO bank_transactions (
    id, client_id, external_id, occurred_on, amount, description,
    counterparty_rut, currency, status, raw_data
) VALUES (
    '7b000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    'TX-INVARIANT-001', DATE '2026-10-16', 100000,
    'Transferencia de prueba', 'TEST-PAYER', 'CLP', 'matched', '{}'::json
);

INSERT INTO reconciliation_proposals (
    id, client_id, bank_transaction_id, candidate_key, status, score, score_breakdown
) VALUES (
    '7c000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '7b000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    'confirmed', 100, '{"rut":{"points":45},"amount":{"points":40},"date":{"points":15}}'::json
);

INSERT INTO reconciliation_items (
    id, client_id, proposal_id, invoice_id, allocated_amount
) VALUES (
    '7d000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '7c000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001', 100000
);

INSERT INTO payments (
    id, client_id, invoice_id, amount, paid_on, verified,
    bank_transaction_id, source, reference, idempotency_key
) VALUES (
    '7e000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    100000, DATE '2026-10-16', TRUE,
    '7b000000-0000-0000-0000-000000000001',
    'bank_statement', 'TX-INVARIANT-001', 'bank:invariant:invoice-1'
);

DO $$
BEGIN
    BEGIN
        INSERT INTO payments (
            id, client_id, invoice_id, amount, paid_on, verified,
            bank_transaction_id, source, reference, idempotency_key
        ) VALUES (
            '7e000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            100000, DATE '2026-10-16', TRUE,
            '7b000000-0000-0000-0000-000000000001',
            'bank_statement', 'TX-INVARIANT-001', 'bank:invariant:duplicate'
        );
        RAISE EXCEPTION 'bank transaction double counting check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO payments (
            id, client_id, invoice_id, amount, paid_on, verified, source
        ) VALUES (
            '7e000000-0000-0000-0000-000000000003',
            '10000000-0000-0000-0000-000000000001',
            '30000000-0000-0000-0000-000000000001',
            -1, DATE '2026-10-16', FALSE, 'manual'
        );
        RAISE EXCEPTION 'positive payment amount check failed';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO reconciliation_proposals (
            id, client_id, bank_transaction_id, candidate_key,
            status, score, score_breakdown
        ) VALUES (
            '7c000000-0000-0000-0000-000000000002',
            '10000000-0000-0000-0000-000000000001',
            '7b000000-0000-0000-0000-000000000001',
            'otro-candidato', 'confirmed', 80, '{}'::json
        );
        RAISE EXCEPTION 'single confirmed reconciliation check failed';
    EXCEPTION
        WHEN unique_violation THEN NULL;
    END;
END;
$$;

INSERT INTO payment_attributions (
    id, client_id, payment_id, invoice_id, contract_id, category,
    percentage, base_amount, commission_amount, rationale, calculated_by
) VALUES (
    '7f000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '7e000000-0000-0000-0000-000000000001',
    '30000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000001',
    'preventive_on_time', 2.5, 100000, 2500,
    '{"rule":"invariant"}'::json, 'contract_rules_v1'
);

DO $$
BEGIN
    BEGIN
        UPDATE payment_attributions SET commission_amount = 1
        WHERE id = '7f000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'payment attribution immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'payment attributions are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO users (
    id, email, full_name, password_hash, role, active
) VALUES (
    '11000000-0000-0000-0000-000000000001',
    'audit@example.test', 'Auditor de prueba', 'not-used', 'ADMIN', true
);

INSERT INTO data_access_logs (
    id, request_id, user_id, actor_role, client_id, method, path,
    status_code, duration_ms, remote_hash, user_agent
) VALUES (
    '12000000-0000-0000-0000-000000000001',
    '12000000-0000-0000-0000-000000000002',
    '11000000-0000-0000-0000-000000000001',
    'admin', '10000000-0000-0000-0000-000000000001',
    'GET', '/api/v1/invoices', 200, 4,
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'invariant-test'
);

DO $$
BEGIN
    BEGIN
        DELETE FROM data_access_logs
        WHERE id = '12000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'data access log immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'data access logs are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

INSERT INTO pilot_authorization_events (
    id, client_id, contract_id, action, channels,
    authorized_contact_name, authorized_contact_email, valid_from,
    performed_by, note, idempotency_key
) VALUES (
    '13000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    '50000000-0000-0000-0000-000000000001',
    'approved', '["email"]'::json,
    'Representante Demo', 'representante@example.test', DATE '2026-10-16',
    '11000000-0000-0000-0000-000000000001',
    'Autorización ficticia de prueba', 'pilot-invariant-approval'
);

DO $$
BEGIN
    BEGIN
        UPDATE pilot_authorization_events SET action = 'revoked'
        WHERE id = '13000000-0000-0000-0000-000000000001';
        RAISE EXCEPTION 'pilot authorization immutability check failed';
    EXCEPTION
        WHEN raise_exception THEN
            IF SQLERRM <> 'pilot authorization events are immutable' THEN
                RAISE;
            END IF;
    END;
END;
$$;

SELECT 'PASS postgres schema and invariants' AS result;

