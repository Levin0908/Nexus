"""Storage layer.

Exposes a module-level singleton `storage` bound to the current Settings.
Routes import `storage` directly; tests can monkeypatch the module attribute
or pass a `LocalDiskStorage(tmp_path)` instance to the unit under test.
"""

from __future__ import annotations

from app.core.config import settings
from app.storage.base import Storage
from app.storage.local import LocalDiskStorage

storage: Storage = LocalDiskStorage(settings.storage_root)

__all__ = ["LocalDiskStorage", "Storage", "storage"]
