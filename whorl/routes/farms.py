"""Farms + fields CRUD (scoped to the current user's org)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, User
from whorl.schemas.farm import FarmCreate, FarmResponse, FieldCreate, FieldResponse

router = APIRouter()


def _farm_to_response(f: Farm) -> FarmResponse:
    return FarmResponse(
        id=f.id, name=f.name,
        client_name=f.client_name, contact_email=f.contact_email, notes=f.notes,
    )


def _field_to_response(f: Field) -> FieldResponse:
    return FieldResponse(
        id=f.id, farm_id=f.farm_id, name=f.name, crop=f.crop,
        acres=f.acres, centroid_lat=f.centroid_lat, centroid_lon=f.centroid_lon,
        planting_date=f.planting_date, variety=f.variety,
    )


@router.get("/api/farms", response_model=list[FarmResponse])
async def list_farms(
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[FarmResponse]:
    rows = (
        await session.execute(
            select(Farm).where(Farm.org_id == user.org_id).order_by(Farm.created_at.desc())
        )
    ).scalars().all()
    return [_farm_to_response(f) for f in rows]


@router.post("/api/farms", response_model=FarmResponse, status_code=201)
async def create_farm(
    body: FarmCreate,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FarmResponse:
    farm = Farm(
        org_id=user.org_id, name=body.name,
        client_name=body.client_name, contact_email=body.contact_email, notes=body.notes,
    )
    session.add(farm)
    await session.commit()
    await session.refresh(farm)
    return _farm_to_response(farm)


@router.get("/api/farms/{farm_id}/fields", response_model=list[FieldResponse])
async def list_fields(
    farm_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[FieldResponse]:
    farm = (
        await session.execute(
            select(Farm).where(Farm.id == farm_id, Farm.org_id == user.org_id)
        )
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(status_code=404, detail="farm not found")
    rows = (
        await session.execute(
            select(Field).where(Field.farm_id == farm_id).order_by(Field.name)
        )
    ).scalars().all()
    return [_field_to_response(f) for f in rows]


@router.post("/api/farms/{farm_id}/fields", response_model=FieldResponse, status_code=201)
async def create_field(
    farm_id: UUID,
    body: FieldCreate,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> FieldResponse:
    farm = (
        await session.execute(
            select(Farm).where(Farm.id == farm_id, Farm.org_id == user.org_id)
        )
    ).scalar_one_or_none()
    if farm is None:
        raise HTTPException(status_code=404, detail="farm not found")
    field = Field(
        farm_id=farm_id, name=body.name, crop=body.crop, acres=body.acres,
        centroid_lat=body.centroid_lat, centroid_lon=body.centroid_lon,
        planting_date=body.planting_date, variety=body.variety,
    )
    session.add(field)
    await session.commit()
    await session.refresh(field)
    return _field_to_response(field)
