"""Scout + identification request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScoutCreate(BaseModel):
    field_id: UUID
    notes: str | None = None


class ScoutResponse(BaseModel):
    id: UUID
    field_id: UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    summary: str | None
    notes: str | None


class IdentificationResponse(BaseModel):
    id: UUID
    rank: int
    taxon_scientific: str
    taxon_common: str | None
    lifecycle_stage: str
    confidence: float
    features: list[str]
    evidence: str


class PhotoWithIds(BaseModel):
    photo_id: UUID
    thumb_path: str
    sha256: str
    uploaded_at: datetime
    identifications: list[IdentificationResponse]


class ScoutDetail(BaseModel):
    scout: ScoutResponse
    photos: list[PhotoWithIds]
