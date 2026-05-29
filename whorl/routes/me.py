"""GET /api/me — current user + org."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from whorl.auth import current_user_with_org
from whorl.models import Organization, User
from whorl.schemas.auth import MeResponse

router = APIRouter()


@router.get("/api/me", response_model=MeResponse)
async def me(
    user_org: Annotated[tuple[User, Organization], Depends(current_user_with_org)],
) -> MeResponse:
    user, org = user_org
    return MeResponse(
        user_id=str(user.id),
        org_id=str(org.id),
        org_name=org.name,
        org_type=org.type,
        email=user.email,
        name=user.name,
    )
