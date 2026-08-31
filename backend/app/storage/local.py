"""Local-disk implementation of the Storage Protocol."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.storage.base import Storage


class LocalDiskStorage(Storage):
    """Stores blobs on the local filesystem under a single root directory.

    Keys are forward-slash relative paths. Nested keys auto-create their parent
    directories on write. Writes are atomic via a `tmp + os.replace` dance so a
    crash mid-write never leaves a half-written file at the target key.
    """

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)

    @property
    def root(self) -> Path:
        return self._root

    def _resolve(self, key: str) -> Path:
        if not key or key.startswith(("/", "\\")) or ".." in Path(key).parts:
            raise ValueError(f"invalid storage key: {key!r}")
        return self._root / key

    def put(self, key: str, data: bytes) -> None:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def size(self, key: str) -> int:
        return self._resolve(key).stat().st_size
