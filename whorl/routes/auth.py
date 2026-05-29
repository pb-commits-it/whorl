"""Magic-link auth routes: request, verify, logout."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import (
    SESSION_COOKIE,
    create_magic_token,
    issue_session_token,
    redeem_magic_token,
)
from whorl.db import get_session
from whorl.models import Organization, User
from whorl.models._common import new_uuid
from whorl.schemas.auth import MagicLinkRequest, MagicLinkResponse

router = APIRouter()


@router.post("/api/auth/magic", response_model=MagicLinkResponse)
async def request_magic_link(
    body: MagicLinkRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MagicLinkResponse:
    settings = request.app.state.settings
    email = body.email.strip().lower()
    if "@" not in email or len(email) < 5:
        raise HTTPException(status_code=400, detail="invalid email")

    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        if body.org_type not in {"farmer", "agronomist"}:
            raise HTTPException(status_code=400, detail="org_type must be 'farmer' or 'agronomist'")
        org = Organization(
            id=new_uuid(),
            name=body.name or email.split("@")[0],
            type=body.org_type,
        )
        session.add(org)
        await session.flush()
        user = User(
            id=new_uuid(),
            org_id=org.id,
            email=email,
            name=body.name,
            role="owner",
        )
        session.add(user)
        await session.flush()

    token = await create_magic_token(
        session, user_id=user.id, ttl_minutes=settings.magic_link_ttl_minutes
    )
    link = f"{settings.base_url}/api/auth/verify?token={token}"
    if settings.whorl_dev_auth:
        print(f"\n[whorl dev auth] magic link for {email}: {link}\n", flush=True)
        return MagicLinkResponse(sent=True, dev_link=link)
    # TODO v0.3: send via Resend.
    return MagicLinkResponse(sent=True, dev_link=None)


@router.get("/api/auth/verify")
async def verify_magic_link(
    token: str,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    user = await redeem_magic_token(session, token)
    if user is None:
        raise HTTPException(status_code=400, detail="token invalid or expired")
    settings = request.app.state.settings
    session_token = issue_session_token(
        user_id=str(user.id),
        org_id=str(user.org_id),
        secret=settings.jwt_secret,
        lifetime_days=settings.jwt_lifetime_days,
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=settings.jwt_lifetime_days * 86400,
        httponly=True,
        samesite="lax",
        secure=False,   # set True in production behind TLS
        path="/",
    )
    return {"ok": True, "user_id": str(user.id), "redirect": "/app"}


@router.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}
