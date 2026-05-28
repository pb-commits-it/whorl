"""Schemas for the photo identification pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LifecycleStage = Literal[
    "egg", "larva", "nymph", "adult", "damage_only", "disease", "unknown"
]
ImageQuality = Literal["good", "marginal", "poor"]
Evidence = Literal["organism", "damage_only"]


class Candidate(BaseModel):
    """A single pest / disease candidate from the vision pass."""

    model_config = ConfigDict(extra="ignore")

    scientific_name: str
    common_name: str = ""
    lifecycle_stage: LifecycleStage = "unknown"
    confidence: float = Field(ge=0.0, le=1.0)
    visible_features: list[str] = Field(default_factory=list)
    evidence: Evidence = "organism"


class VisionResult(BaseModel):
    """Structured response from one vision pass on one photo."""

    model_config = ConfigDict(extra="ignore")

    candidates: list[Candidate] = Field(default_factory=list)
    image_quality: ImageQuality = "good"
    notes: str = ""


class PhotoUploadResponse(BaseModel):
    photo_id: str
    stored_path: str
    thumb_path: str
    sha256: str
    width: int
    height: int
    bytes: int
    vision: VisionResult
    model_used: str
