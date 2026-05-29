"""Signed JWT session tokens (HS256)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TypedDict

from jose import JWTError, jwt


class SessionPayload(TypedDict):
    user_id: str
    org_id: str
    exp: int


def issue_session_token(*, user_id: str, org_id: str, secret: str, lifetime_days: int) -> str:
    expires = datetime.now(tz=timezone.utc) + timedelta(days=lifetime_days)
    return jwt.encode(
        {"user_id": user_id, "org_id": org_id, "exp": int(expires.timestamp())},
        secret,
        algorithm="HS256",
    )


def verify_session_token(token: str, secret: str) -> SessionPayload | None:
    try:
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        return SessionPayload(
            user_id=decoded["user_id"],
            org_id=decoded["org_id"],
            exp=decoded["exp"],
        )
    except (JWTError, KeyError, ValueError, TypeError):
        return None
