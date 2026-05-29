"""FastAPI dependencies that resolve the current user from the session cookie."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth.jwt import verify_session_token
from whorl.db import get_session
from whorl.models import Organization, User

SESSION_COOKIE = "whorl_session"


async def current_user(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    whorl_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    if not whorl_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    settings = request.app.state.settings
    payload = verify_session_token(whorl_session, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="invalid session")
    user = (
        await session.execute(select(User).where(User.id == UUID(payload["user_id"])))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="user not found")
    return user


async def current_user_with_org(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> tuple[User, Organization]:
    org = (
        await session.execute(select(Organization).where(Organization.id == user.org_id))
    ).scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=401, detail="organization not found")
    return user, org
