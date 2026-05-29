"""Recommender endpoints: generate + fetch latest per-scout recommendation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from whorl.auth import current_user
from whorl.db import get_session
from whorl.models import Farm, Field, Recommendation, Scout, User
from whorl.pipeline.recommend import PROMPT_VERSION, generate_recommendation
from whorl.schemas.recommend import (
    Alternative,
    ChemicalRecommendation,
    Citation,
    RecommendationResponse,
    RecommendationResult,
    SprayWindow,
)

router = APIRouter()


async def _authz_scout(
    session: AsyncSession, scout_id: UUID, org_id: UUID
) -> Scout:
    scout = (await session.execute(
        select(Scout).join(Field, Scout.field_id == Field.id)
        .join(Farm, Field.farm_id == Farm.id)
        .where(Scout.id == scout_id, Farm.org_id == org_id)
    )).scalar_one_or_none()
    if scout is None:
        raise HTTPException(status_code=404, detail="scout not found")
    return scout


def _rec_to_result(rec: Recommendation) -> RecommendationResult:
    return RecommendationResult(
        action=rec.action,
        pest_focus=rec.pest_focus,
        threshold_context=rec.threshold_context or "",
        spray_window=SprayWindow(**rec.spray_window) if rec.spray_window else None,
        chemical=ChemicalRecommendation(**rec.chemical) if rec.chemical else None,
        alternatives=[Alternative(**a) for a in (rec.alternatives or [])],
        plain_english=rec.plain_english,
        confidence=rec.confidence,
        citations=[Citation(**c) for c in (rec.citations or [])],
    )


@router.post("/api/scouts/{scout_id}/recommend", response_model=RecommendationResponse)
async def make_recommendation(
    scout_id: UUID,
    request: Request,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecommendationResponse:
    scout = await _authz_scout(session, scout_id, user.org_id)
    settings = request.app.state.settings

    try:
        result, model_used, latency_ms = await generate_recommendation(
            session, scout_id, settings
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    rec = Recommendation(
        scout_id=scout_id,
        action=result.action,
        pest_focus=result.pest_focus,
        confidence=result.confidence,
        plain_english=result.plain_english,
        threshold_context=result.threshold_context,
        chemical=result.chemical.model_dump() if result.chemical else None,
        spray_window=result.spray_window.model_dump() if result.spray_window else None,
        alternatives=[a.model_dump() for a in result.alternatives],
        citations=[c.model_dump() for c in result.citations],
        model_used=model_used,
        prompt_version=PROMPT_VERSION,
        latency_ms=latency_ms,
    )
    session.add(rec)

    # Mark scout complete with the recommendation summary.
    scout.status = "complete"
    scout.completed_at = datetime.now(UTC).replace(tzinfo=None)
    scout.summary = result.pest_focus
    await session.commit()
    await session.refresh(rec)

    return RecommendationResponse(
        id=str(rec.id),
        scout_id=str(scout_id),
        result=result,
        model_used=model_used,
        prompt_version=PROMPT_VERSION,
        latency_ms=latency_ms,
        created_at=rec.created_at.isoformat(),
    )


@router.get(
    "/api/scouts/{scout_id}/recommendation",
    response_model=RecommendationResponse | None,
)
async def get_recommendation(
    scout_id: UUID,
    user: Annotated[User, Depends(current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> RecommendationResponse | None:
    await _authz_scout(session, scout_id, user.org_id)
    rec = (await session.execute(
        select(Recommendation)
        .where(Recommendation.scout_id == scout_id)
        .order_by(Recommendation.created_at.desc())
    )).scalars().first()
    if rec is None:
        return None
    return RecommendationResponse(
        id=str(rec.id),
        scout_id=str(scout_id),
        result=_rec_to_result(rec),
        model_used=rec.model_used,
        prompt_version=rec.prompt_version,
        latency_ms=rec.latency_ms or 0,
        created_at=rec.created_at.isoformat(),
    )
