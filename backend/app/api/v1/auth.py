from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    password_hasher,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


def _build_token_response(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject=subject),
        refresh_token=create_refresh_token(subject=subject),
        expires_in=settings.jwt_access_ttl_minutes * 60,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(body: RegisterRequest, db: DbSession) -> TokenResponse:
    email = body.email.lower()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        )

    user = User(
        email=email,
        password_hash=password_hasher.hash(body.password),
    )
    db.add(user)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="email already registered",
        ) from None

    await db.refresh(user)
    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DbSession) -> TokenResponse:
    email = body.email.lower()

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="account disabled",
        )

    if not password_hasher.verify(user.password_hash, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )

    return _build_token_response(user)
