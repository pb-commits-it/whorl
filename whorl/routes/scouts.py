"""Scouts: create, list per field, detail with photos + identifications."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, Identification, Photo, Scout, User
from whorl.schemas.scout import (
    IdentificationResponse,
    PhotoWithIds,
    ScoutCreate,
    ScoutDetail,
    ScoutResponse,
)

router = APIRouter()


def _scout_response(s: Scout) -> ScoutResponse:
    return ScoutResponse(
        id=s.id, field_id=s.field_id, status=s.status,
        started_at=s.started_at, completed_at=s.completed_at,
        summary=s.summary, notes=s.notes,
    )


async def _field_in_org(session: AsyncSession, field_id: UUID, org_id: UUID) -> Field | None:
    return (
        await session.execute(
            select(Field).join(Farm, Field.farm_id == Farm.id)
            .where(Field.id == field_id, Farm.org_id == org_id)
        )
    ).scalar_one_or_none()


@router.post("/api/scouts", response_model=ScoutResponse, status_code=201)
async def create_scout(
    body: ScoutCreate,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScoutResponse:
    field = await _field_in_org(session, body.field_id, user.org_id)
    if field is None:
        raise HTTPException(status_code=404, detail="field not found")
    scout = Scout(field_id=body.field_id, user_id=user.id, notes=body.notes)
    session.add(scout)
    await session.commit()
    await session.refresh(scout)
    return _scout_response(scout)


@router.get("/api/fields/{field_id}/scouts", response_model=list[ScoutResponse])
async def list_scouts_for_field(
    field_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ScoutResponse]:
    field = await _field_in_org(session, field_id, user.org_id)
    if field is None:
        raise HTTPException(status_code=404, detail="field not found")
    rows = (
        await session.execute(
            select(Scout).where(Scout.field_id == field_id).order_by(Scout.started_at.desc())
        )
    ).scalars().all()
    return [_scout_response(s) for s in rows]


@router.get("/api/scouts/{scout_id}", response_model=ScoutDetail)
async def get_scout_detail(
    scout_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ScoutDetail:
    scout = (
        await session.execute(
            select(Scout).join(Field, Scout.field_id == Field.id)
            .join(Farm, Field.farm_id == Farm.id)
            .where(Scout.id == scout_id, Farm.org_id == user.org_id)
        )
    ).scalar_one_or_none()
    if scout is None:
        raise HTTPException(status_code=404, detail="scout not found")

    photos = (
        await session.execute(
            select(Photo).where(Photo.scout_id == scout_id).order_by(Photo.uploaded_at)
        )
    ).scalars().all()
    photo_payloads: list[PhotoWithIds] = []
    for p in photos:
        ids = (
            await session.execute(
                select(Identification)
                .where(Identification.photo_id == p.id)
                .order_by(Identification.rank)
            )
        ).scalars().all()
        photo_payloads.append(PhotoWithIds(
            photo_id=p.id,
            thumb_path=p.thumb_path,
            sha256=p.sha256,
            uploaded_at=p.uploaded_at,
            identifications=[
                IdentificationResponse(
                    id=i.id, rank=i.rank,
                    taxon_scientific=i.taxon_scientific, taxon_common=i.taxon_common,
                    lifecycle_stage=i.lifecycle_stage, confidence=i.confidence,
                    features=i.features or [], evidence=i.evidence,
                )
                for i in ids
            ],
        ))
    return ScoutDetail(scout=_scout_response(scout), photos=photo_payloads)
