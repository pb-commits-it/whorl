"""Magic-link token creation + redemption (DB-backed, single-use, TTL-bound)."""

from __future__ import annotations

import secrets
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.models import AuthToken, User
from whorl.models._common import now_utc


def _new_token() -> str:
    # 32 bytes ≈ 43 base64url chars; the AuthToken.token column is 80 chars.
    return secrets.token_urlsafe(32)


async def create_magic_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    ttl_minutes: int,
) -> str:
    token = _new_token()
    expires = now_utc() + timedelta(minutes=ttl_minutes)
    session.add(AuthToken(token=token, user_id=user_id, expires_at=expires))
    await session.commit()
    return token


async def redeem_magic_token(session: AsyncSession, token: str) -> User | None:
    """Atomically consume the token and return the User. None if invalid/expired/used."""
    row = (
        await session.execute(select(AuthToken).where(AuthToken.token == token))
    ).scalar_one_or_none()
    if row is None or row.used_at is not None or row.expires_at <= now_utc():
        return None
    row.used_at = now_utc()
    user = (
        await session.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if user is None:
        return None
    user.last_login_at = now_utc()
    await session.commit()
    return user
