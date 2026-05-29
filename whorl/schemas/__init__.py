"""Pydantic request/response models."""

from whorl.schemas.auth import MagicLinkRequest, MagicLinkResponse, MeResponse
from whorl.schemas.farm import FarmCreate, FarmResponse, FieldCreate, FieldResponse
from whorl.schemas.photo import Candidate, PhotoUploadResponse, VisionResult
from whorl.schemas.scout import (
    IdentificationResponse,
    PhotoWithIds,
    ScoutCreate,
    ScoutDetail,
    ScoutResponse,
)

__all__ = [
    "Candidate",
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
    "ScoutCreate",
    "ScoutDetail",
    "ScoutResponse",
    "VisionResult",
]
