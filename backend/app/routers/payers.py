import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import Invoice, Payer, PayerProfile, PayerProfileRevision, User
from app.routers.invoices import _authorized_client
from app.schemas import (
    PayerProfileRevisionView,
    PayerProfileUpdate,
    PayerProfileView,
    PayerView,
)
from app.security import CurrentUser, require_roles
from app.services.payability import (
    create_profile_revision,
    ensure_checklist,
    get_or_create_profile,
    profile_version,
)


router = APIRouter(prefix="/api/v1/payers", tags=["payers"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


def _payer_access(
    db: Session, user: CurrentUser, payer_id: uuid.UUID, client_id: uuid.UUID | None
) -> tuple[Payer, uuid.UUID | None]:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise HTTPException(status_code=404, detail="Pagador no encontrado")
    if user.role == Role.CLIENT:
        scoped_client = _authorized_client(user, client_id)
        associated = db.scalar(
            select(Invoice.id)
            .where(Invoice.client_id == scoped_client, Invoice.payer_id == payer_id)
            .limit(1)
        )
        if associated is None:
            raise HTTPException(status_code=404, detail="Pagador no asociado a la empresa")
        return payer, scoped_client
    return payer, client_id


@router.get("", response_model=list[PayerView])
def list_payers(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[Payer]:
    scoped_client = _authorized_client(user, client_id)
    return list(
        db.scalars(
            select(Payer)
            .join(Invoice, Invoice.payer_id == Payer.id)
            .where(Invoice.client_id == scoped_client)
            .distinct()
            .order_by(Payer.legal_name)
        )
    )


@router.get("/{payer_id}/profile", response_model=PayerProfileView)
def get_profile(
    payer_id: uuid.UUID,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> dict:
    _payer_access(db, user, payer_id, client_id)
    profile = get_or_create_profile(db, payer_id)
    db.commit()
    db.refresh(profile)
    return {
        **profile.__dict__,
        "version": profile_version(db, profile.id),
    }


@router.put("/{payer_id}/profile", response_model=PayerProfileView)
def update_profile(
    payer_id: uuid.UUID,
    payload: PayerProfileUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    payer = db.get(Payer, payer_id)
    if payer is None:
        raise HTTPException(status_code=404, detail="Pagador no encontrado")
    profile = get_or_create_profile(db, payer_id)
    profile = db.scalar(
        select(PayerProfile).where(PayerProfile.id == profile.id).with_for_update()
    )
    assert profile is not None
    profile.operational_requirements = payload.operational_requirements.model_dump(mode="json")
    profile.supplier_portal_url = payload.supplier_portal_url
    profile.supplier_portal_instructions = payload.supplier_portal_instructions
    profile.corporate_channels = payload.corporate_channels
    profile.payment_cycle = payload.payment_cycle
    db.flush()
    revision = create_profile_revision(db, profile, actor_id=user.id)

    invoices = list(db.scalars(select(Invoice).where(Invoice.payer_id == payer_id)))
    for invoice in invoices:
        ensure_checklist(db, invoice, actor_type=ActorType.HUMAN, actor_id=user.id)
    for client_id in {invoice.client_id for invoice in invoices}:
        record_event(
            db,
            client_id=client_id,
            event_type="payer_profile.updated",
            actor_type=ActorType.HUMAN,
            actor_id=user.id,
            payload={
                "payer_id": str(payer_id),
                "profile_id": str(profile.id),
                "version": revision.version,
            },
        )
    db.commit()
    db.refresh(profile)
    return {**profile.__dict__, "version": revision.version}


@router.get("/{payer_id}/profile/revisions", response_model=list[PayerProfileRevisionView])
def list_profile_revisions(
    payer_id: uuid.UUID,
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> list[PayerProfileRevision]:
    profile = db.scalar(select(PayerProfile).where(PayerProfile.payer_id == payer_id))
    if profile is None:
        return []
    return list(
        db.scalars(
            select(PayerProfileRevision)
            .where(PayerProfileRevision.payer_profile_id == profile.id)
            .order_by(PayerProfileRevision.version.desc())
        )
    )
