import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import EmailStr
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.document_crypto import encrypt_document_content
from app.domain import ActorType, Role
from app.models import (
    Client,
    Contact,
    Contract,
    Document,
    Invoice,
    MessageTemplate,
    PilotAuthorizationEvent,
    PilotLogEntry,
    User,
)
from app.schemas import (
    DemoWalkthroughView,
    PilotAuthorizationRevoke,
    PilotAuthorizationView,
    PilotLogCreate,
    PilotLogEntryView,
    PilotLogResolve,
    PilotReadinessView,
)
from app.security import require_roles
from app.services.pilot_operations import build_demo_walkthrough


router = APIRouter(prefix="/api/v1/pilot", tags=["pilot-readiness"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]
ALLOWED_CHANNELS = {"email", "whatsapp_assisted"}


def _latest_authorization(db: Session, client_id: uuid.UUID) -> PilotAuthorizationEvent | None:
    return db.scalar(
        select(PilotAuthorizationEvent)
        .where(PilotAuthorizationEvent.client_id == client_id)
        .order_by(PilotAuthorizationEvent.created_at.desc(), PilotAuthorizationEvent.id.desc())
        .limit(1)
    )


@router.get("/authorizations", response_model=list[PilotAuthorizationView])
def list_authorizations(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> list[PilotAuthorizationEvent]:
    return list(
        db.scalars(
            select(PilotAuthorizationEvent)
            .where(PilotAuthorizationEvent.client_id == client_id)
            .order_by(PilotAuthorizationEvent.created_at.desc())
        )
    )


@router.post("/authorizations", response_model=PilotAuthorizationView, status_code=201)
async def approve_pilot_authorization(
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
    evidence: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID, Form()],
    contract_id: Annotated[uuid.UUID, Form()],
    channels_json: Annotated[str, Form()],
    authorized_contact_name: Annotated[str, Form(min_length=2, max_length=200)],
    authorized_contact_email: Annotated[EmailStr, Form()],
    valid_from: Annotated[date, Form()],
    valid_until: Annotated[date | None, Form()] = None,
    note: Annotated[str | None, Form(max_length=2000)] = None,
) -> PilotAuthorizationEvent:
    client = db.get(Client, client_id)
    contract = db.scalar(
        select(Contract).where(
            Contract.id == contract_id,
            Contract.client_id == client_id,
            Contract.active.is_(True),
        )
    )
    if client is None or contract is None:
        raise HTTPException(status_code=409, detail="Cliente o contrato activo no válido")
    try:
        channels = sorted(set(json.loads(channels_json)))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="channels_json debe ser una lista JSON") from exc
    if not channels or not set(channels).issubset(ALLOWED_CHANNELS):
        raise HTTPException(status_code=422, detail="Canales autorizados no válidos")
    if valid_until is not None and valid_until < valid_from:
        raise HTTPException(status_code=422, detail="valid_until no puede ser anterior a valid_from")
    content = await evidence.read()
    if not content:
        raise HTTPException(status_code=422, detail="La evidencia de autorización está vacía")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="La evidencia supera 10 MB")
    digest = hashlib.sha256(content).hexdigest()
    idempotency_key = hashlib.sha256(
        f"{client_id}:{contract_id}:{authorized_contact_email}:{valid_from}:{digest}".encode()
    ).hexdigest()
    existing = db.scalar(
        select(PilotAuthorizationEvent).where(
            PilotAuthorizationEvent.idempotency_key == idempotency_key
        )
    )
    if existing is not None:
        return existing
    document_id = uuid.uuid4()
    ciphertext, nonce, version = encrypt_document_content(
        document_id=document_id,
        client_id=client_id,
        invoice_id=None,
        content=content,
    )
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", evidence.filename or "autorizacion.bin")
    document = Document(
        id=document_id,
        client_id=client_id,
        kind="pilot_authorization",
        object_key=f"local-pilot-authorization/{client_id}/{digest}/{safe_name}",
        original_name=safe_name,
        sha256=digest,
        content=ciphertext,
        encryption_version=version,
        encryption_nonce=nonce,
    )
    db.add(document)
    db.flush()
    authorization = PilotAuthorizationEvent(
        client_id=client_id,
        contract_id=contract_id,
        action="approved",
        channels=channels,
        authorized_contact_name=authorized_contact_name.strip(),
        authorized_contact_email=str(authorized_contact_email).lower(),
        valid_from=valid_from,
        valid_until=valid_until,
        evidence_document_id=document.id,
        performed_by=user.id,
        note=note,
        idempotency_key=idempotency_key,
    )
    db.add(authorization)
    db.flush()
    record_event(
        db,
        client_id=client_id,
        event_type="pilot.authorization_recorded",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "authorization_id": str(authorization.id),
            "contract_id": str(contract_id),
            "channels": channels,
            "valid_from": valid_from.isoformat(),
            "valid_until": valid_until.isoformat() if valid_until else None,
            "evidence_document_id": str(document.id),
            "evidence_sha256": digest,
        },
    )
    db.commit()
    db.refresh(authorization)
    return authorization


@router.post(
    "/authorizations/{authorization_id}/revoke",
    response_model=PilotAuthorizationView,
    status_code=201,
)
def revoke_pilot_authorization(
    authorization_id: uuid.UUID,
    payload: PilotAuthorizationRevoke,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PilotAuthorizationEvent:
    current = db.scalar(
        select(PilotAuthorizationEvent).where(
            PilotAuthorizationEvent.id == authorization_id,
            PilotAuthorizationEvent.client_id == payload.client_id,
            PilotAuthorizationEvent.action == "approved",
        )
    )
    if current is None:
        raise HTTPException(status_code=404, detail="Autorización vigente no encontrada")
    latest = _latest_authorization(db, payload.client_id)
    if latest is None or latest.id != current.id:
        raise HTTPException(status_code=409, detail="La autorización ya fue reemplazada o revocada")
    revocation = PilotAuthorizationEvent(
        client_id=current.client_id,
        contract_id=current.contract_id,
        action="revoked",
        channels=current.channels,
        authorized_contact_name=current.authorized_contact_name,
        authorized_contact_email=current.authorized_contact_email,
        valid_from=current.valid_from,
        valid_until=current.valid_until,
        supersedes_id=current.id,
        performed_by=user.id,
        note=payload.note,
        idempotency_key=f"revoke:{current.id}",
    )
    db.add(revocation)
    db.flush()
    record_event(
        db,
        client_id=current.client_id,
        event_type="pilot.authorization_revoked",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "authorization_id": str(current.id),
            "revocation_id": str(revocation.id),
            "note": payload.note,
        },
    )
    db.commit()
    db.refresh(revocation)
    return revocation


@router.get("/readiness", response_model=PilotReadinessView)
def pilot_readiness(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
) -> dict:
    contract = db.scalar(
        select(Contract).where(Contract.client_id == client_id, Contract.active.is_(True))
    )
    channels = sorted(set((contract.rules or {}).get("channels", []))) if contract else []
    latest = _latest_authorization(db, client_id)
    today = date.today()
    authorization_valid = bool(
        latest
        and latest.action == "approved"
        and contract
        and latest.contract_id == contract.id
        and set(channels).issubset(set(latest.channels))
        and latest.valid_from <= today
        and (latest.valid_until is None or latest.valid_until >= today)
    )
    templates = list(
        db.scalars(
            select(MessageTemplate).where(
                MessageTemplate.client_id == client_id,
                MessageTemplate.active.is_(True),
                MessageTemplate.approved.is_(True),
            )
        )
    )
    approved_template_channels = {template.channel for template in templates}
    contacts = list(db.scalars(select(Contact).where(Contact.client_id == client_id)))
    contact_channels = set()
    if any(contact.email and not contact.opted_out_email for contact in contacts):
        contact_channels.add("email")
    if any(contact.phone and not contact.opted_out_whatsapp for contact in contacts):
        contact_channels.add("whatsapp_assisted")
    legacy_documents = int(
        db.scalar(
            select(func.count(Document.id)).where(
                Document.client_id == client_id,
                Document.content.is_not(None),
                or_(
                    Document.encryption_version.is_(None),
                    Document.encryption_version != "aesgcm-v1",
                ),
            )
        )
        or 0
    )
    checks = {
        "active_contract": contract is not None,
        "authorized_channels": authorization_valid,
        "approved_templates": bool(channels) and set(channels).issubset(approved_template_channels),
        "eligible_contacts": bool(channels) and set(channels).issubset(contact_channels),
        "documents_encrypted": legacy_documents == 0,
    }
    labels = {
        "active_contract": "Falta un contrato activo.",
        "authorized_channels": "Falta autorización vigente con evidencia para el contrato y sus canales.",
        "approved_templates": "Faltan plantillas aprobadas para todos los canales contratados.",
        "eligible_contacts": "Faltan contactos habilitados para todos los canales contratados.",
        "documents_encrypted": "Existen documentos legados sin cifrado AES-GCM.",
    }
    return {
        "client_id": client_id,
        "ready": all(checks.values()),
        "checks": checks,
        "blockers": [labels[key] for key, passed in checks.items() if not passed],
        "active_contract_id": contract.id if contract else None,
        "required_channels": channels,
        "authorization": latest,
    }


@router.get("/log", response_model=list[PilotLogEntryView])
def list_pilot_log(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[str | None, Query(pattern="^(open|resolved)$")] = None,
    entry_type: Annotated[
        str | None,
        Query(pattern="^(decision|incident|manual_work|rule_change|learning)$"),
    ] = None,
) -> list[PilotLogEntry]:
    query = select(PilotLogEntry).where(PilotLogEntry.client_id == client_id)
    if status is not None:
        query = query.where(PilotLogEntry.status == status)
    if entry_type is not None:
        query = query.where(PilotLogEntry.entry_type == entry_type)
    return list(
        db.scalars(
            query.order_by(
                PilotLogEntry.occurred_on.desc(),
                PilotLogEntry.created_at.desc(),
                PilotLogEntry.id.desc(),
            ).limit(500)
        )
    )


@router.post("/log", response_model=PilotLogEntryView, status_code=201)
def create_pilot_log_entry(
    payload: PilotLogCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PilotLogEntry:
    client = db.get(Client, payload.client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if payload.related_invoice_id is not None:
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.id == payload.related_invoice_id,
                Invoice.client_id == payload.client_id,
            )
        )
        if invoice is None:
            raise HTTPException(status_code=404, detail="Factura relacionada no encontrada")
    created_at = datetime.now(timezone.utc)
    immediately_closed = payload.entry_type != "incident"
    entry = PilotLogEntry(
        client_id=payload.client_id,
        related_invoice_id=payload.related_invoice_id,
        entry_type=payload.entry_type,
        severity=payload.severity,
        title=payload.title.strip(),
        detail=payload.detail.strip(),
        status="resolved" if immediately_closed else "open",
        occurred_on=payload.occurred_on,
        human_minutes=payload.human_minutes,
        created_by=user.id,
        resolved_by=user.id if immediately_closed else None,
        resolved_at=created_at if immediately_closed else None,
        resolution_note="Registro completo al crear." if immediately_closed else None,
    )
    db.add(entry)
    db.flush()
    record_event(
        db,
        client_id=entry.client_id,
        invoice_id=entry.related_invoice_id,
        event_type="pilot.log_recorded",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="manual",
        payload={
            "pilot_log_entry_id": str(entry.id),
            "entry_type": entry.entry_type,
            "severity": entry.severity,
            "title": entry.title,
            "occurred_on": entry.occurred_on.isoformat(),
            "human_minutes": str(entry.human_minutes),
            "status": entry.status,
        },
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/log/{entry_id}/resolve", response_model=PilotLogEntryView)
def resolve_pilot_log_entry(
    entry_id: uuid.UUID,
    payload: PilotLogResolve,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> PilotLogEntry:
    entry = db.scalar(
        select(PilotLogEntry)
        .where(
            PilotLogEntry.id == entry_id,
            PilotLogEntry.client_id == payload.client_id,
        )
        .with_for_update()
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Registro del piloto no encontrado")
    if entry.status != "open":
        raise HTTPException(status_code=409, detail="El registro ya está resuelto")
    entry.status = "resolved"
    entry.resolved_by = user.id
    entry.resolved_at = datetime.now(timezone.utc)
    entry.resolution_note = payload.resolution_note.strip()
    record_event(
        db,
        client_id=entry.client_id,
        invoice_id=entry.related_invoice_id,
        event_type="pilot.log_resolved",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        mode="manual",
        payload={
            "pilot_log_entry_id": str(entry.id),
            "resolution_note": entry.resolution_note,
        },
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/demo-walkthrough", response_model=DemoWalkthroughView)
def demo_walkthrough(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    operation_date: Annotated[date | None, Query()] = None,
) -> dict:
    client = db.get(Client, client_id)
    if client is None or not client.active:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return build_demo_walkthrough(
        db,
        client=client,
        operation_date=operation_date or date.today(),
    )
