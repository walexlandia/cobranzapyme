import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, Role
from app.models import Client, User
from app.schemas import ClientBaselineUpdate, ClientCreate, ClientView
from app.security import require_roles
from app.utils.rut import normalize_rut


router = APIRouter(prefix="/api/v1/clients", tags=["clients"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


@router.get("", response_model=list[ClientView])
def list_clients(_: Operator, db: Annotated[Session, Depends(get_db)]) -> list[Client]:
    return list(db.scalars(select(Client).order_by(Client.name)))


@router.post("", response_model=ClientView, status_code=201)
def create_client(
    payload: ClientCreate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    try:
        client = Client(
            name=payload.name,
            rut=normalize_rut(payload.rut),
            industry=payload.industry.strip() if payload.industry else None,
            sender_name=payload.sender_name,
            sender_email=str(payload.sender_email) if payload.sender_email else None,
            bank_details=payload.bank_details,
            baseline_dso=payload.baseline_dso,
            baseline_on_time_percent=payload.baseline_on_time_percent,
            baseline_late_distribution=payload.baseline_late_distribution,
        )
        db.add(client)
        db.flush()
        record_event(
            db,
            client_id=client.id,
            event_type="client.created",
            actor_type=ActorType.HUMAN,
            actor_id=user.id,
            payload={"name": client.name, "rut": client.rut},
        )
        db.commit()
        db.refresh(client)
        return client
    except (ValueError, IntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/{client_id}/baseline", response_model=ClientView)
def update_baseline(
    client_id: uuid.UUID,
    payload: ClientBaselineUpdate,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    previous = {
        "baseline_dso": str(client.baseline_dso) if client.baseline_dso is not None else None,
        "baseline_on_time_percent": (
            str(client.baseline_on_time_percent)
            if client.baseline_on_time_percent is not None
            else None
        ),
        "baseline_late_distribution": client.baseline_late_distribution,
    }
    client.baseline_dso = payload.baseline_dso
    client.baseline_on_time_percent = payload.baseline_on_time_percent
    client.baseline_late_distribution = payload.baseline_late_distribution
    record_event(
        db,
        client_id=client.id,
        event_type="client.baseline_updated",
        actor_type=ActorType.HUMAN,
        actor_id=user.id,
        payload={
            "from": previous,
            "to": {
                "baseline_dso": str(payload.baseline_dso) if payload.baseline_dso is not None else None,
                "baseline_on_time_percent": (
                    str(payload.baseline_on_time_percent)
                    if payload.baseline_on_time_percent is not None
                    else None
                ),
                "baseline_late_distribution": payload.baseline_late_distribution,
            },
        },
    )
    db.commit()
    db.refresh(client)
    return client

