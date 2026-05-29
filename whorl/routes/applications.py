"""Applications — log pesticide sprays per field; feeds MOA-rotation context."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Application, Farm, Field, User
from whorl.schemas.application import ApplicationCreate, ApplicationResponse

router = APIRouter()


def _app_resp(a: Application) -> ApplicationResponse:
    return ApplicationResponse(
        id=a.id, field_id=a.field_id, applied_at=a.applied_at,
        pest_target=a.pest_target, product_name=a.product_name,
        active_ingredient=a.active_ingredient,
        moa_class=a.moa_class, moa_group=a.moa_group,
        rate=a.rate, units=a.units, epa_reg_no=a.epa_reg_no,
        rei_hours=a.rei_hours, phi_days=a.phi_days,
        outcome=a.outcome, notes=a.notes, created_at=a.created_at,
    )


@router.get("/api/fields/{field_id}/applications", response_model=list[ApplicationResponse])
async def list_applications(
    field_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ApplicationResponse]:
    field = (await session.execute(
        select(Field).join(Farm, Field.farm_id == Farm.id)
        .where(Field.id == field_id, Farm.org_id == user.org_id)
    )).scalar_one_or_none()
    if field is None:
        raise HTTPException(status_code=404, detail="field not found")
    rows = (await session.execute(
        select(Application)
        .where(Application.field_id == field_id)
        .order_by(Application.applied_at.desc())
    )).scalars().all()
    return [_app_resp(a) for a in rows]


@router.post("/api/applications", response_model=ApplicationResponse, status_code=201)
async def create_application(
    body: ApplicationCreate,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ApplicationResponse:
    field = (await session.execute(
        select(Field).join(Farm, Field.farm_id == Farm.id)
        .where(Field.id == body.field_id, Farm.org_id == user.org_id)
    )).scalar_one_or_none()
    if field is None:
        raise HTTPException(status_code=404, detail="field not found")

    applied = body.applied_at
    if applied.tzinfo is not None:
        applied = applied.replace(tzinfo=None)

    app = Application(
        field_id=body.field_id, applied_at=applied,
        pest_target=body.pest_target, product_name=body.product_name,
        active_ingredient=body.active_ingredient,
        moa_class=body.moa_class, moa_group=body.moa_group,
        rate=body.rate, units=body.units, epa_reg_no=body.epa_reg_no,
        rei_hours=body.rei_hours, phi_days=body.phi_days,
        outcome=body.outcome, notes=body.notes,
        recorded_by=user.id,
    )
    session.add(app)
    await session.commit()
    await session.refresh(app)
    return _app_resp(app)
