import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.domain import Role
from app.models import User


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "client_id": str(user.client_id) if user.client_id else None,
        "exp": expires,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, KeyError, ValueError):
        raise unauthorized
    user = db.scalar(select(User).where(User.id == user_id, User.active.is_(True)))
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Permisos insuficientes")
        return user

    return dependency

