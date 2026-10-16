import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.domain import ActorType, InvoiceStatus
from app.models import Invoice, PayabilityItem, PayerProfile, PayerProfileRevision
from app.schemas import PayerRequirements


DEFAULT_REQUIREMENTS = PayerRequirements().model_dump(mode="json")


def get_or_create_profile(db: Session, payer_id: uuid.UUID) -> PayerProfile:
    profile = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == payer_id))
    if profile is None:
        profile = PayerProfile(
            payer_id=payer_id,
            operational_requirements=DEFAULT_REQUIREMENTS,
            corporate_channels={},
        )
        db.add(profile)
        db.flush()
    return profile


def profile_version(db: Session, profile_id: uuid.UUID) -> int:
    return int(
        db.scalar(
            select(func.coalesce(func.max(PayerProfileRevision.version), 0)).where(
                PayerProfileRevision.payer_profile_id == profile_id
            )
        )
        or 0
    )


def profile_snapshot(profile: PayerProfile) -> dict[str, Any]:
    return {
        "operational_requirements": profile.operational_requirements,
        "supplier_portal_url": profile.supplier_portal_url,
        "supplier_portal_instructions": profile.supplier_portal_instructions,
        "corporate_channels": profile.corporate_channels,
        "payment_cycle": profile.payment_cycle,
    }


def create_profile_revision(
    db: Session, profile: PayerProfile, *, actor_id: uuid.UUID | None
) -> PayerProfileRevision:
    revision = PayerProfileRevision(
        payer_profile_id=profile.id,
        version=profile_version(db, profile.id) + 1,
        snapshot=profile_snapshot(profile),
        actor_id=actor_id,
    )
    db.add(revision)
    return revision


def requirement_specs(
    invoice: Invoice, requirements: PayerRequirements
) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = [
        {
            "item_type": "sii_acceptance",
            "label": "Aceptación en SII",
            "required": True,
            "blocks_payability": True,
            "responsible_role": "client",
            "initial_status": "pending",
            "initial_evidence": {},
        },
        {
            "item_type": "purchase_order",
            "label": "Orden de compra",
            "required": requirements.requires_purchase_order,
            "blocks_payability": True,
            "responsible_role": "client",
            "initial_status": (
                "fulfilled"
                if invoice.purchase_order
                else ("pending" if requirements.requires_purchase_order else "not_applicable")
            ),
            "initial_evidence": (
                {"purchase_order": invoice.purchase_order} if invoice.purchase_order else {}
            ),
        },
        {
            "item_type": "hes_conformity",
            "label": "HES o conformidad del servicio",
            "required": requirements.requires_hes,
            "blocks_payability": True,
            "responsible_role": "requester",
            "initial_status": "pending" if requirements.requires_hes else "not_applicable",
            "initial_evidence": {},
        },
        {
            "item_type": "delivery_note",
            "label": "Guía de despacho",
            "required": requirements.requires_delivery_note,
            "blocks_payability": True,
            "responsible_role": "client",
            "initial_status": (
                "pending" if requirements.requires_delivery_note else "not_applicable"
            ),
            "initial_evidence": {},
        },
        {
            "item_type": "supplier_portal",
            "label": "Carga en portal de proveedores",
            "required": requirements.requires_supplier_portal,
            "blocks_payability": True,
            "responsible_role": "client",
            "initial_status": (
                "pending" if requirements.requires_supplier_portal else "not_applicable"
            ),
            "initial_evidence": {},
        },
    ]
    specs.extend(
        {
            "item_type": f"other_{requirement.code}",
            "label": requirement.label,
            "required": True,
            "blocks_payability": True,
            "responsible_role": requirement.responsible_role,
            "initial_status": "pending",
            "initial_evidence": {},
        }
        for requirement in requirements.other_requirements
    )
    specs.extend(
        [
            {
                "item_type": "payment_approval",
                "label": "Aprobación para pago",
                "required": False,
                "blocks_payability": False,
                "responsible_role": "accounts_payable",
                "initial_status": "pending",
                "initial_evidence": {},
            },
            {
                "item_type": "payment_scheduled",
                "label": "Programación de pago",
                "required": False,
                "blocks_payability": False,
                "responsible_role": "accounts_payable",
                "initial_status": "pending",
                "initial_evidence": {},
            },
        ]
    )
    return specs


def ensure_checklist(
    db: Session,
    invoice: Invoice,
    *,
    actor_type: ActorType = ActorType.SYSTEM,
    actor_id: uuid.UUID | None = None,
    emit_events: bool = True,
) -> list[PayabilityItem]:
    profile = get_or_create_profile(db, invoice.payer_id)
    requirements = PayerRequirements.model_validate(profile.operational_requirements)
    existing = {
        item.item_type: item
        for item in db.scalars(
            select(PayabilityItem).where(PayabilityItem.invoice_id == invoice.id)
        )
    }
    active_types: set[str] = set()
    for spec in requirement_specs(invoice, requirements):
        item_type = spec["item_type"]
        active_types.add(item_type)
        item = existing.get(item_type)
        if item is None:
            item = PayabilityItem(
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                item_type=item_type,
                label=spec["label"],
                status=spec["initial_status"],
                required=spec["required"],
                blocks_payability=spec["blocks_payability"],
                responsible_role=spec["responsible_role"],
                evidence=spec["initial_evidence"],
            )
            db.add(item)
            existing[item_type] = item
            if emit_events:
                record_event(
                    db,
                    client_id=invoice.client_id,
                    invoice_id=invoice.id,
                    event_type="payability.item_created",
                    actor_type=actor_type,
                    actor_id=actor_id,
                    payload={
                        "item_type": item_type,
                        "label": item.label,
                        "status": item.status,
                        "required": item.required,
                        "responsible_role": item.responsible_role,
                    },
                )
            continue

        previous = {
            "label": item.label,
            "required": item.required,
            "blocks_payability": item.blocks_payability,
            "responsible_role": item.responsible_role,
            "status": item.status,
        }
        item.label = spec["label"]
        item.required = spec["required"]
        item.blocks_payability = spec["blocks_payability"]
        item.responsible_role = spec["responsible_role"]
        if (
            not item.required
            and item.blocks_payability
            and item.status in {"pending", "requested", "blocked"}
        ):
            item.status = "not_applicable"
        elif item.required and item.status == "not_applicable":
            item.status = spec["initial_status"]
        current = {
            "label": item.label,
            "required": item.required,
            "blocks_payability": item.blocks_payability,
            "responsible_role": item.responsible_role,
            "status": item.status,
        }
        if emit_events and previous != current:
            record_event(
                db,
                client_id=invoice.client_id,
                invoice_id=invoice.id,
                event_type="payability.requirement_changed",
                actor_type=actor_type,
                actor_id=actor_id,
                payload={"item_type": item_type, "from": previous, "to": current},
            )

    for item_type, item in existing.items():
        if item_type.startswith("other_") and item_type not in active_types and item.required:
            item.required = False
            if item.status in {"pending", "requested", "blocked"}:
                item.status = "not_applicable"
            if emit_events:
                record_event(
                    db,
                    client_id=invoice.client_id,
                    invoice_id=invoice.id,
                    event_type="payability.requirement_changed",
                    actor_type=actor_type,
                    actor_id=actor_id,
                    payload={"item_type": item_type, "required": False},
                )
    db.flush()
    return sorted(existing.values(), key=lambda item: (not item.blocks_payability, item.label))


def checklist_status(
    invoice: Invoice,
    items: list[PayabilityItem],
    *,
    requirements: PayerRequirements,
    today: date | None = None,
) -> tuple[str, int, int, list[str]]:
    evaluation_date = today or date.today()
    blocking = [item for item in items if item.required and item.blocks_payability]
    completed = [item for item in blocking if item.status in {"fulfilled", "not_applicable"}]
    missing = [item.label for item in blocking if item.status not in {"fulfilled", "not_applicable"}]
    sii_item = next((item for item in items if item.item_type == "sii_acceptance"), None)
    sii_status = (sii_item.evidence or {}).get("sii_status") if sii_item else None
    raw_claim_deadline = (sii_item.evidence or {}).get("claim_deadline") if sii_item else None
    try:
        claim_deadline = date.fromisoformat(raw_claim_deadline) if raw_claim_deadline else None
    except (TypeError, ValueError):
        claim_deadline = None
    if invoice.status in {InvoiceStatus.CLAIMED, InvoiceStatus.DISPUTED} or sii_status in {
        "claimed",
        "rejected",
    }:
        status = "claimed"
    elif blocking and len(completed) == len(blocking):
        status = "payable"
    elif (
        sii_status == "pending"
        and claim_deadline is not None
        and evaluation_date > claim_deadline
    ) or evaluation_date >= invoice.due_on - timedelta(days=requirements.risk_days_before_due):
        status = "at_risk"
    else:
        status = "incomplete"
    return status, len(completed), len(blocking), missing


def annotate_invoice_payability(
    db: Session, invoices: list[Invoice], *, today: date | None = None
) -> None:
    if not invoices:
        return
    invoice_ids = [invoice.id for invoice in invoices]
    items_by_invoice: dict[uuid.UUID, list[PayabilityItem]] = {
        invoice_id: [] for invoice_id in invoice_ids
    }
    for item in db.scalars(
        select(PayabilityItem).where(PayabilityItem.invoice_id.in_(invoice_ids))
    ):
        items_by_invoice[item.invoice_id].append(item)
    profiles = {
        profile.payer_id: profile
        for profile in db.scalars(
            select(PayerProfile).where(
                PayerProfile.payer_id.in_({invoice.payer_id for invoice in invoices})
            )
        )
    }
    for invoice in invoices:
        profile = profiles.get(invoice.payer_id)
        requirements = PayerRequirements.model_validate(
            profile.operational_requirements if profile else DEFAULT_REQUIREMENTS
        )
        status, completed, total, _ = checklist_status(
            invoice, items_by_invoice[invoice.id], requirements=requirements, today=today
        )
        invoice.payability_status = status
        invoice.payability_completed = completed
        invoice.payability_total = total
