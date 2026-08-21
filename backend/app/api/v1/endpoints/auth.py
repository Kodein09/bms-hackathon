from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_user_by_login,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas import RefreshRequest, Token, UserCreate, UserRead


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
    existing_user = await db.scalar(
        select(User).where(or_(User.username == user_data.username, User.email == user_data.email))
    )
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already exists")

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        position=user_data.position,
        hashed_password=hash_password(user_data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    user = await get_user_by_login(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    try:
        payload = jwt.decode(
            request.refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        if payload.get("type") != "refresh" or not payload.get("sub"):
            raise ValueError
        user_id = UUID(payload["sub"])
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from None

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user
