from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.db.models import User


def _require_sessionmaker(request: Request) -> async_sessionmaker[AsyncSession]:
    sm = getattr(request.app.state, "db_sessionmaker", None)
    if sm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not configured",
        )
    return sm


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    sm = _require_sessionmaker(request)
    async with sm() as session:
        yield session


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise _unauthorized("Invalid Authorization header")
    return parts[1].strip()


async def _get_or_create_user(*, db: AsyncSession, external_id: str) -> User:
    ext = (external_id or "").strip()
    if not ext:
        raise _unauthorized("Token missing 'sub' claim")

    existing = (
        await db.execute(select(User).where(User.external_id == ext))
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    now = datetime.now(timezone.utc)
    user = User(id=uuid.uuid4(), external_id=ext, created_at=now, updated_at=now)
    db.add(user)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        # Handle possible race: another request created the user concurrently.
        existing = (
            await db.execute(select(User).where(User.external_id == ext))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        raise
    await db.refresh(user)
    return user


async def get_current_user(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = _extract_bearer_token(authorization)
    if token is None:
        raise _unauthorized()

    settings = get_settings()
    secret = (settings.supabase_jwt_secret or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase auth not configured",
        )

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise _unauthorized("Token expired") from exc
    except InvalidTokenError as exc:
        raise _unauthorized("Invalid token") from exc

    sub = payload.get("sub")
    return await _get_or_create_user(
        db=db, external_id=str(sub) if sub is not None else ""
    )


async def get_optional_user(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Optional[User]:
    token = _extract_bearer_token(authorization)
    if token is None:
        return None

    # Only require DB when a token is actually provided.
    sm = _require_sessionmaker(request)
    async with sm() as db:
        settings = get_settings()
        secret = (settings.supabase_jwt_secret or "").strip()
        if not secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase auth not configured",
            )

        try:
            payload = jwt.decode(token, secret, algorithms=["HS256"])
        except ExpiredSignatureError as exc:
            raise _unauthorized("Token expired") from exc
        except InvalidTokenError as exc:
            raise _unauthorized("Invalid token") from exc

        sub = payload.get("sub")
        return await _get_or_create_user(
            db=db, external_id=str(sub) if sub is not None else ""
        )
