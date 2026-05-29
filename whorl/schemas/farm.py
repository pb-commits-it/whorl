"""Farm + field request/response schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class FarmCreate(BaseModel):
    name: str
    client_name: str | None = None
    contact_email: str | None = None
    notes: str | None = None


class FarmResponse(BaseModel):
    id: UUID
    name: str
    client_name: str | None
    contact_email: str | None
    notes: str | None


class FieldCreate(BaseModel):
    name: str
    crop: str
    acres: float | None = None
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    planting_date: date | None = None
    variety: str | None = None


class FieldResponse(BaseModel):
    id: UUID
    farm_id: UUID
    name: str
    crop: str
    acres: float | None
    centroid_lat: float | None
    centroid_lon: float | None
    planting_date: date | None
    variety: str | None
