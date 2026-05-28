"""Local-disk photo storage behind an `ObjectStore` protocol.

v1 uses local disk; v1.x can swap to Cloudflare R2 by implementing `ObjectStore`.
Layout on disk:  {root}/{org_id}/{yyyy}/{mm}/{photo_id}.{ext} + {photo_id}_thumb.jpg
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from PIL import Image


@dataclass
class StoredPhoto:
    photo_id: str
    path: str
    thumb_path: str
    sha256: str
    width: int
    height: int
    bytes_: int


class ObjectStore(Protocol):
    def put(self, data: bytes, ext: str, *, org_id: str = "default") -> StoredPhoto: ...
    def open(self, path: str) -> bytes: ...


class LocalDiskStore:
    """Stores photos on the local filesystem under `root`."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, ext: str, *, org_id: str = "default") -> StoredPhoto:
        photo_id = uuid4().hex[:12]
        now = datetime.now(tz=timezone.utc)
        rel = Path(org_id) / f"{now.year}" / f"{now.month:02d}"
        full = self.root / rel
        full.mkdir(parents=True, exist_ok=True)
        raw_path = full / f"{photo_id}.{ext}"
        thumb_path = full / f"{photo_id}_thumb.jpg"

        raw_path.write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()

        with Image.open(raw_path) as im:
            width, height = im.size
            im.thumbnail((512, 512))
            im.convert("RGB").save(thumb_path, "JPEG", quality=82)

        return StoredPhoto(
            photo_id=photo_id,
            path=str(raw_path),
            thumb_path=str(thumb_path),
            sha256=sha,
            width=width,
            height=height,
            bytes_=len(data),
        )

    def open(self, path: str) -> bytes:
        return Path(path).read_bytes()
