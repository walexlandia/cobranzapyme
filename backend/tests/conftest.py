import uuid
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.domain import Role
from app.models import Client, Invoice, Payer, User
from app.security import hash_password


@pytest.fixture
def db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def create_tenant_user(
    db: Session,
    *,
    suffix: str,
    role: Role = Role.CLIENT,
) -> tuple[Client, User]:
    client = Client(
        name=f"Pyme {suffix}",
        rut=f"TEST-{uuid.uuid4()}",
        bank_details={},
    )
    db.add(client)
    db.flush()
    user = User(
        email=f"{suffix}-{uuid.uuid4()}@example.test",
        full_name=f"Usuario {suffix}",
        password_hash=hash_password("TestPassword123!"),
        role=role,
        client_id=client.id if role == Role.CLIENT else None,
    )
    db.add(user)
    db.commit()
    return client, user


def create_invoice(db: Session, tenant: Client, folio: str) -> Invoice:
    payer = Payer(rut=f"TEST-{uuid.uuid4()}", legal_name=f"Pagador {folio}")
    db.add(payer)
    db.flush()
    invoice = Invoice(
        client_id=tenant.id,
        payer_id=payer.id,
        folio=folio,
        issued_on=date(2026, 1, 10),
        due_on=date(2026, 2, 9),
        total_amount=100000,
    )
    db.add(invoice)
    db.commit()
    return invoice

