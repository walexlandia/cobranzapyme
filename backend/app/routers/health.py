from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.version import DATABASE_MIGRATION_HEAD


router = APIRouter(tags=["health"])


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/health/version")
def version() -> dict[str, str]:
    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "database_migration_head": DATABASE_MIGRATION_HEAD,
    }

