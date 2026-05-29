"""Recommender request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SprayWindow(BaseModel):
    open: str
    close: str
    reason: str


class ChemicalRecommendation(BaseModel):
    product: str
    active_ingredient: str
    moa_class: Literal["IRAC", "FRAC", "HRAC"]
    moa_group: str
    rotation_rationale: str
    rei_hours: int
    phi_days: int


class Alternative(BaseModel):
    category: Literal["biological", "cultural", "mechanical"]
    name: str
    summary: str
    kb_link: str


class Citation(BaseModel):
    chunk_id: int
    quote: str


class RecommendationResult(BaseModel):
    """Structured output the recommender LLM must return."""

    model_config = ConfigDict(extra="ignore")

    action: Literal["no_action", "monitor", "scout_again", "treat"]
    pest_focus: str
    threshold_context: str = ""
    spray_window: SprayWindow | None = None
    chemical: ChemicalRecommendation | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    plain_english: str
    confidence: Literal["high", "medium", "low"]
    citations: list[Citation] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    """What the recommendation API returns to the client."""

    id: str
    scout_id: str
    result: RecommendationResult
    model_used: str
    prompt_version: str
    latency_ms: int
    created_at: str
