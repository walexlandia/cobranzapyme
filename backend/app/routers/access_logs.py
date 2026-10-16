import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Role
from app.models import DataAccessLog, User
from app.schemas import DataAccessLogView
from app.security import require_roles


router = APIRouter(prefix="/api/v1/access-logs", tags=["security-and-access"])
Admin = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("", response_model=list[DataAccessLogView])
def list_access_logs(
    _: Admin,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    since: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[DataAccessLog]:
    query = select(DataAccessLog)
    if client_id:
        query = query.where(DataAccessLog.client_id == client_id)
    if user_id:
        query = query.where(DataAccessLog.user_id == user_id)
    if since:
        query = query.where(DataAccessLog.created_at >= since)
    return list(db.scalars(query.order_by(DataAccessLog.created_at.desc()).limit(limit)))
