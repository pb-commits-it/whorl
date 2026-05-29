"""POST /api/photos — upload to an existing scout, run vision, persist identifications."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, Identification, Photo, Scout, User
from whorl.pipeline.vision import identify
from whorl.schemas.photo import PhotoUploadResponse

router = APIRouter()

ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}


@router.post("/api/photos", response_model=PhotoUploadResponse)
async def upload_photo(
    request: Request,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    scout_id: Annotated[UUID, Form(...)],
    file: Annotated[UploadFile, File(...)],
    crop: Annotated[str | None, Form()] = None,
    state: Annotated[str | None, Form()] = None,
) -> PhotoUploadResponse:
    # Authz: scout must belong to a field in this user's org.
    scout = (
        await session.execute(
            select(Scout).join(Field, Scout.field_id == Field.id)
            .join(Farm, Field.farm_id == Farm.id)
            .where(Scout.id == scout_id, Farm.org_id == user.org_id)
        )
    ).scalar_one_or_none()
    if scout is None:
        raise HTTPException(status_code=404, detail="scout not found")
    field = (
        await session.execute(select(Field).where(Field.id == scout.field_id))
    ).scalar_one()

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "jpg"
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {ext}")

    store = request.app.state.photo_store
    settings = request.app.state.settings
    hub = request.app.state.hub
    stored = store.put(data, ext, org_id=str(user.org_id))

    await hub.publish("photo_uploaded", {
        "scout_id": str(scout.id),
        "thumb_path": stored.thumb_path,
        "sha256": stored.sha256,
    })

    result, model_used = await identify(
        stored.thumb_path, settings,
        crop=crop or field.crop, state=state, date_iso=date.today().isoformat(),
    )

    photo = Photo(
        scout_id=scout.id, storage_path=stored.path, thumb_path=stored.thumb_path,
        sha256=stored.sha256, width=stored.width, height=stored.height, bytes=stored.bytes_,
    )
    session.add(photo)
    await session.flush()

    for rank, c in enumerate(result.candidates, start=1):
        session.add(Identification(
            photo_id=photo.id,
            rank=rank,
            taxon_scientific=c.scientific_name,
            taxon_common=c.common_name,
            lifecycle_stage=c.lifecycle_stage,
            confidence=c.confidence,
            features=c.visible_features,
            evidence=c.evidence,
            image_quality=result.image_quality,
            notes=result.notes,
            model_used=model_used,
        ))
    await session.commit()

    # Confidence flag (v0.5): top candidate < 0.55 → recommender will pivot to
    # scout_again; < 0.75 → low-confidence yellow border in the UI.
    top_conf = result.candidates[0].confidence if result.candidates else 0.0
    low_confidence = top_conf < 0.75
    needs_rescout = top_conf < 0.55 or not result.candidates

    await hub.publish("id_ready", {
        "scout_id": str(scout.id),
        "photo_id": str(photo.id),
        "thumb_path": stored.thumb_path,
        "candidates": [c.model_dump() for c in result.candidates],
        "image_quality": result.image_quality,
        "top_confidence": top_conf,
        "low_confidence": low_confidence,
        "needs_rescout": needs_rescout,
    })

    return PhotoUploadResponse(
        photo_id=str(photo.id),
        stored_path=stored.path,
        thumb_path=stored.thumb_path,
        sha256=stored.sha256,
        width=stored.width,
        height=stored.height,
        bytes=stored.bytes_,
        vision=result,
        model_used=model_used,
    )
