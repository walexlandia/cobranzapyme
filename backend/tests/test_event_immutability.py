import uuid

import pytest
from sqlalchemy import delete, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.domain import ActorType
from app.models import Client, Event


def test_events_cannot_be_updated_or_deleted(db: Session) -> None:
    client = Client(name="Audit Test", rut=f"TEST-{uuid.uuid4()}", bank_details={})
    db.add(client)
    db.flush()
    event = Event(
        client_id=client.id,
        event_type="audit.test",
        actor_type=ActorType.SYSTEM,
        payload={"original": True},
    )
    db.add(event)
    db.commit()

    with pytest.raises(DBAPIError):
        db.execute(update(Event).where(Event.id == event.id).values(event_type="changed"))
        db.commit()
    db.rollback()

    with pytest.raises(DBAPIError):
        db.execute(delete(Event).where(Event.id == event.id))
        db.commit()
    db.rollback()

