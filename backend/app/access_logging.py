import hashlib
import time
import uuid

import jwt
from jwt import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings
from app.database import SessionLocal
from app.models import DataAccessLog


class AuthenticatedAccessLogMiddleware(BaseHTTPMiddleware):
    """Record authenticated API access without persisting tokens or request bodies."""

    async def dispatch(self, request: Request, call_next):
        started = time.monotonic()
        response = await call_next(request)
        authorization = request.headers.get("authorization", "")
        if request.url.path.startswith("/api/v1/") and authorization.startswith("Bearer "):
            try:
                payload = jwt.decode(
                    authorization.removeprefix("Bearer ").strip(),
                    settings.jwt_secret,
                    algorithms=[settings.jwt_algorithm],
                )
                user_id = uuid.UUID(payload["sub"])
                raw_client_id = payload.get("client_id")
                if raw_client_id is None and response.status_code < 400:
                    raw_client_id = request.query_params.get("client_id")
                try:
                    client_id = uuid.UUID(raw_client_id) if raw_client_id else None
                except (ValueError, TypeError):
                    client_id = None
                remote = request.client.host if request.client else None
                remote_hash = (
                    hashlib.sha256(f"{settings.jwt_secret}:{remote}".encode()).hexdigest()
                    if remote
                    else None
                )
                log = DataAccessLog(
                    request_id=uuid.uuid4(),
                    user_id=user_id,
                    actor_role=str(payload.get("role", "unknown")),
                    client_id=client_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=max(0, round((time.monotonic() - started) * 1000)),
                    remote_hash=remote_hash,
                    user_agent=request.headers.get("user-agent", "")[:300] or None,
                )
                with SessionLocal() as db:
                    db.add(log)
                    db.commit()
                response.headers["X-Request-ID"] = str(log.request_id)
            except (InvalidTokenError, KeyError, ValueError, TypeError):
                pass
            except Exception:
                # Telemetry must never make the business request fail.
                pass
        return response
