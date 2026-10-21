import uuid
from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.base import Base
from app.database import SessionLocal, engine
from app.main import app
from app.domain import Role
from app.models import Client, Invoice, Payer, User
from app.security import hash_password


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None, None, None]:
    """Keep integration tests independent while preserving the migrated schema."""
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    yield


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
        rut=f"T{uuid.uuid4().hex[:11]}",
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
    payer = Payer(rut=f"P{uuid.uuid4().hex[:11]}", legal_name=f"Pagador {folio}")
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

