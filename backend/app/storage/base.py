"""Storage abstraction.

A Protocol that lets the app treat files uniformly regardless of where they
physically live. The local-disk implementation is the default for development;
an S3-compatible implementation can be added later (Phase 7) without touching
call sites.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """A blob store keyed by a relative string path.

    Keys are forward-slash separated, relative to the storage root. The
    implementation is responsible for translating them into whatever physical
    location it owns (a directory on disk, a bucket prefix on S3, etc.).
    """

    def put(self, key: str, data: bytes) -> None:
        """Write `data` to the given key, creating parent dirs as needed."""
        ...

    def get(self, key: str) -> bytes:
        """Read and return the bytes at `key`. Raises FileNotFoundError if missing."""
        ...

    def delete(self, key: str) -> None:
        """Remove the object at `key`. No-op if missing."""
        ...

    def exists(self, key: str) -> bool:
        """True if an object exists at `key`."""
        ...

    def size(self, key: str) -> int:
        """Byte size of the object at `key`. Raises FileNotFoundError if missing."""
        ...
