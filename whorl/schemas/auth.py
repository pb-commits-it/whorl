"""Auth + identity request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MagicLinkRequest(BaseModel):
    email: str = Field(max_length=255)   # validity checked in the route (returns 400)
    org_type: str = "farmer"             # 'farmer' | 'agronomist' (only used on first signup)
    name: str | None = None


class MagicLinkResponse(BaseModel):
    sent: bool
    dev_link: str | None = None   # in dev mode the link is returned inline so the UI can follow it


class MeResponse(BaseModel):
    user_id: str
    org_id: str
    org_name: str
    org_type: str
    email: str
    name: str | None = None
