"""LocalDiskStore: writes original + thumbnail, returns metadata."""

from __future__ import annotations

from pathlib import Path

from whorl.storage.photos import LocalDiskStore


def test_local_disk_store_roundtrip(tmp_path: Path, jpeg_bytes: bytes):
    store = LocalDiskStore(tmp_path / "photos")

    stored = store.put(jpeg_bytes, "jpg", org_id="org-test")

    assert Path(stored.path).exists()
    assert Path(stored.thumb_path).exists()
    assert stored.width == 16
    assert stored.height == 16
    assert stored.bytes_ == len(jpeg_bytes)
    assert len(stored.sha256) == 64
    assert "org-test" in stored.path
    # round-trip read
    assert store.open(stored.path) == jpeg_bytes
