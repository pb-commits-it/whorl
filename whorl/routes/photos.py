"""POST /api/photos — multipart photo upload + vision pass."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from whorl.pipeline.vision import identify
from whorl.schemas.photo import PhotoUploadResponse

router = APIRouter()

ALLOWED_EXTS = {"jpg", "jpeg", "png", "webp"}


@router.post("/api/photos", response_model=PhotoUploadResponse)
async def upload_photo(
    request: Request,
    file: UploadFile = File(...),
    crop: str | None = Form(default=None),
    state: str | None = Form(default=None),
) -> PhotoUploadResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() or "jpg"
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {ext}")

    store = request.app.state.photo_store
    settings = request.app.state.settings
    stored = store.put(data, ext)

    result, model_used = await identify(
        stored.thumb_path,
        settings,
        crop=crop,
        state=state,
        date_iso=date.today().isoformat(),
    )

    return PhotoUploadResponse(
        photo_id=stored.photo_id,
        stored_path=stored.path,
        thumb_path=stored.thumb_path,
        sha256=stored.sha256,
        width=stored.width,
        height=stored.height,
        bytes=stored.bytes_,
        vision=result,
        model_used=model_used,
    )
