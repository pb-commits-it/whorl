"""Treatment-history (Application) schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ApplicationCreate(BaseModel):
    field_id: UUID
    applied_at: datetime
    pest_target: str | None = None
    product_name: str
    active_ingredient: str | None = None
    moa_class: Literal["IRAC", "FRAC", "HRAC"] | None = None
    moa_group: str | None = None
    rate: str | None = None
    units: str | None = None
    epa_reg_no: str | None = None
    rei_hours: int | None = None
    phi_days: int | None = None
    outcome: str | None = None
    notes: str | None = None


class ApplicationResponse(BaseModel):
    id: UUID
    field_id: UUID
    applied_at: datetime
    pest_target: str | None
    product_name: str
    active_ingredient: str | None
    moa_class: str | None
    moa_group: str | None
    rate: str | None
    units: str | None
    epa_reg_no: str | None
    rei_hours: int | None
    phi_days: int | None
    outcome: str | None
    notes: str | None
    created_at: datetime
