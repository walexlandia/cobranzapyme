from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserView
from app.security import CurrentUser, create_access_token, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


@router.post("/token", response_model=Token)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = db.scalar(select(User).where(User.email == form.username.lower(), User.active.is_(True)))
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return Token(access_token=create_access_token(user))


@router.get("/me", response_model=UserView)
def me(user: CurrentUser) -> User:
    return user

