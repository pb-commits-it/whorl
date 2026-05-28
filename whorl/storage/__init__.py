"""Photo storage — local disk for v1, behind an `ObjectStore` protocol."""

from whorl.storage.photos import LocalDiskStore, ObjectStore, StoredPhoto

__all__ = ["LocalDiskStore", "ObjectStore", "StoredPhoto"]
