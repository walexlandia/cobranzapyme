import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain import ActorType
from app.models import Event


def record_event(
    db: Session,
    *,
    client_id: uuid.UUID,
    event_type: str,
    actor_type: ActorType,
    actor_id: uuid.UUID | None = None,
    invoice_id: uuid.UUID | None = None,
    mode: str = "manual",
    payload: dict[str, Any] | None = None,
) -> Event:
    event = Event(
        client_id=client_id,
        invoice_id=invoice_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_id=actor_id,
        mode=mode,
        payload=payload or {},
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event

