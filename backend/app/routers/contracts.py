import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import Client, Contract, User
from app.routers.invoices import _authorized_client
from app.schemas import ContractActivate, ContractCreate, ContractView
from app.security import CurrentUser, require_roles


router = APIRouter(prefix="/api/v1/contracts", tags=["contracts"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


@router.get("", response_model=list[ContractView])
def list_contracts(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    client_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[Contract]:
    scoped_client = _authorized_client(user, client_id)
    return list(
        db.scalars(
            select(Contract)
            .where(Contract.client_id == scoped_client)
            .order_by(Contract.version.desc())
        )
    )


@router.post("", response_model=ContractView, status_code=201)
def create_contract(
    payload: ContractCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Contract:
    client = db.scalar(select(Client).where(Client.id == payload.client_id).with_for_update())
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    next_version = (
        db.scalar(select(func.coalesce(func.max(Contract.version), 0)).where(Contract.client_id == client.id))
        or 0
    ) + 1
    if payload.activate:
        db.execute(update(Contract).where(Contract.client_id == client.id).values(active=False))

    contract = Contract(
        client_id=client.id,
        version=next_version,
        rules=payload.rules.model_dump(mode="json"),
        active=payload.activate,
    )
    db.add(contract)
    db.flush()
    record_event(
        db,
        client_id=client.id,
        event_type="contract.created",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={"contract_id": str(contract.id), "version": contract.version, "active": contract.active},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflicto al crear la versión del contrato") from exc
    db.refresh(contract)
    return contract


@router.post("/{contract_id}/activate", response_model=ContractView)
def activate_contract(
    contract_id: uuid.UUID,
    payload: ContractActivate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Contract:
    contract = db.scalar(
        select(Contract).where(Contract.id == contract_id, Contract.client_id == payload.client_id)
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    db.execute(update(Contract).where(Contract.client_id == payload.client_id).values(active=False))
    contract.active = True
    record_event(
        db,
        client_id=contract.client_id,
        event_type="contract.activated",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={"contract_id": str(contract.id), "version": contract.version},
    )
    db.commit()
    db.refresh(contract)
    return contract
