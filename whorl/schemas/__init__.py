"""Pydantic request/response models."""

from whorl.schemas.application import ApplicationCreate, ApplicationResponse
from whorl.schemas.auth import MagicLinkRequest, MagicLinkResponse, MeResponse
from whorl.schemas.farm import FarmCreate, FarmResponse, FieldCreate, FieldResponse
from whorl.schemas.photo import Candidate, PhotoUploadResponse, VisionResult
from whorl.schemas.recommend import (
    Alternative,
    ChemicalRecommendation,
    Citation,
    RecommendationResponse,
    RecommendationResult,
    SprayWindow,
)
from whorl.schemas.scout import (
    IdentificationResponse,
    PhotoWithIds,
    ScoutCreate,
    ScoutDetail,
    ScoutResponse,
)

__all__ = [
    "Alternative",
    "ApplicationCreate",
    "ApplicationResponse",
    "Candidate",
    "ChemicalRecommendation",
    "Citation",
    "FarmCreate",
    "FarmResponse",
    "FieldCreate",
    "FieldResponse",
    "IdentificationResponse",
    "MagicLinkRequest",
    "MagicLinkResponse",
    "MeResponse",
    "PhotoUploadResponse",
    "PhotoWithIds",
    "RecommendationResponse",
    "RecommendationResult",
    "ScoutCreate",
    "ScoutDetail",
    "ScoutResponse",
    "SprayWindow",
    "VisionResult",
]
