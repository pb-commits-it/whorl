"""Public landing-page waitlist signup. No auth.

Idempotent: re-submitting the same email is a 200 with `subscribed: true`
rather than a 409, so a refresh after a network blip doesn't look like an
error to the user.
"""

from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.db import get_session
from whorl.models import WaitlistEntry

router = APIRouter()

# Permissive on TLD length to match modern gTLDs; rejects spaces and most
# obvious garbage. Real email validation happens by sending a release-note
# email and observing delivery, not here.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


class WaitlistSignup(BaseModel):
    email: str
    source: str | None = None


class WaitlistResponse(BaseModel):
    subscribed: bool


@router.post("/api/waitlist", response_model=WaitlistResponse)
async def signup(
    body: WaitlistSignup,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WaitlistResponse:
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="not a valid email address")
    if len(email) > 320:
        raise HTTPException(status_code=400, detail="email too long")

    existing = (await session.execute(
        select(WaitlistEntry).where(WaitlistEntry.email == email)
    )).scalar_one_or_none()
    if existing is not None:
        return WaitlistResponse(subscribed=True)

    ua = request.headers.get("user-agent", "")[:512]
    ip = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip() \
        or (request.client.host if request.client else None)
    session.add(WaitlistEntry(email=email, source=body.source, user_agent=ua, ip=ip))
    await session.commit()
    return WaitlistResponse(subscribed=True)
