import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.domain import Role
from app.models import GuidedWorkSession, User
from app.schemas import (
    GuidedWorkCancel,
    GuidedWorkComplete,
    GuidedWorkGuideView,
    GuidedWorkSessionView,
    GuidedWorkStart,
)
from app.security import require_roles
from app.services.guided_work import (
    benchmark_for_sessions,
    cancel_guided_work,
    complete_guided_work,
    guide_payload,
    start_guided_work,
)

router = APIRouter(prefix="/api/v1/optimizations", tags=["guided-optimization"])
Operator = Annotated[User, Depends(require_roles(Role.ADMIN, Role.OPERATOR))]


@router.get("/weekly-portfolio-review/guide", response_model=GuidedWorkGuideView)
def get_weekly_review_guide(_: Operator) -> dict:
    return guide_payload()


@router.post(
    "/weekly-portfolio-review/sessions",
    response_model=GuidedWorkSessionView,
    status_code=201,
)
def start_weekly_review(
    payload: GuidedWorkStart,
    response: Response,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> GuidedWorkSession:
    session, created = start_guided_work(db, payload=payload, actor=user)
    if not created:
        response.status_code = 200
    return session


@router.get(
    "/weekly-portfolio-review/sessions",
    response_model=list[GuidedWorkSessionView],
)
def list_weekly_reviews(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID,
    status: Annotated[
        str | None, Query(pattern="^(open|completed|cancelled)$")
    ] = None,
) -> list[GuidedWorkSession]:
    query = select(GuidedWorkSession).where(GuidedWorkSession.client_id == client_id)
    if status is not None:
        query = query.where(GuidedWorkSession.status == status)
    return list(
        db.scalars(
            query.order_by(
                GuidedWorkSession.created_at.desc(), GuidedWorkSession.id.desc()
            ).limit(200)
        )
    )


@router.post(
    "/weekly-portfolio-review/sessions/{session_id}/complete",
    response_model=GuidedWorkSessionView,
)
def complete_weekly_review(
    session_id: uuid.UUID,
    payload: GuidedWorkComplete,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> GuidedWorkSession:
    return complete_guided_work(db, session_id=session_id, payload=payload, actor=user)


@router.post(
    "/weekly-portfolio-review/sessions/{session_id}/cancel",
    response_model=GuidedWorkSessionView,
)
def cancel_weekly_review(
    session_id: uuid.UUID,
    payload: GuidedWorkCancel,
    user: Operator,
    db: Annotated[Session, Depends(get_db)],
) -> GuidedWorkSession:
    return cancel_guided_work(
        db, session_id=session_id, reason=payload.reason, actor=user
    )


@router.get("/weekly-portfolio-review/benchmark")
def get_weekly_review_benchmark(
    _: Operator,
    db: Annotated[Session, Depends(get_db)],
    client_id: uuid.UUID | None = None,
) -> dict:
    return benchmark_for_sessions(db, client_id=client_id)
