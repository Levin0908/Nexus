"""Local-disk implementation of the Storage Protocol."""

from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO

from app.storage.base import Storage

_WRITE_CHUNK = 64 * 1024


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

    def _atomic_write(self, target: Path, write: Callable[[BinaryIO], None]) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "wb") as f:
                write(f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, target)
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise

    def put(self, key: str, data: bytes) -> None:
        def write(f: BinaryIO) -> None:
            f.write(data)

        self._atomic_write(self._resolve(key), write)

    def put_file_obj(self, key: str, fp: BinaryIO) -> None:
        """Stream bytes from a file-like object to storage without buffering."""
        if hasattr(fp, "seek"):
            fp.seek(0)

        def write(f: BinaryIO) -> None:
            while True:
                chunk = fp.read(_WRITE_CHUNK)
                if not chunk:
                    break
                f.write(chunk)

        self._atomic_write(self._resolve(key), write)

    def get(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        path.unlink(missing_ok=True)

    def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    def size(self, key: str) -> int:
        return self._resolve(key).stat().st_size
