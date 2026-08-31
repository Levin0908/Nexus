from pathlib import Path

import pytest

from app.storage.local import LocalDiskStorage


@pytest.fixture
def store(tmp_path: Path) -> LocalDiskStorage:
    return LocalDiskStorage(tmp_path)


async def test_put_and_get_roundtrip(store: LocalDiskStorage, tmp_path: Path) -> None:
    payload = b"hello, world"
    store.put("a/b/file.txt", payload)

    assert store.exists("a/b/file.txt") is True
    assert store.get("a/b/file.txt") == payload
    assert store.size("a/b/file.txt") == len(payload)
    assert (tmp_path / "a" / "b" / "file.txt").is_file()


async def test_put_overwrites_existing(store: LocalDiskStorage) -> None:
    store.put("k.txt", b"first")
    store.put("k.txt", b"second")
    assert store.get("k.txt") == b"second"
    assert store.size("k.txt") == 6


async def test_get_missing_raises(store: LocalDiskStorage) -> None:
    with pytest.raises(FileNotFoundError):
        store.get("does/not/exist.bin")


async def test_delete_removes_object(store: LocalDiskStorage) -> None:
    store.put("temp.txt", b"bye")
    assert store.exists("temp.txt")
    store.delete("temp.txt")
    assert store.exists("temp.txt") is False


async def test_delete_missing_is_noop(store: LocalDiskStorage) -> None:
    store.delete("nope.txt")


async def test_exists_false_for_missing(store: LocalDiskStorage) -> None:
    assert store.exists("nothing.txt") is False


async def test_size_missing_raises(store: LocalDiskStorage) -> None:
    with pytest.raises(FileNotFoundError):
        store.size("missing.txt")


def test_root_is_created_if_missing(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "store"
    LocalDiskStorage(target)
    assert target.is_dir()


def test_rejects_absolute_key(store: LocalDiskStorage) -> None:
    with pytest.raises(ValueError):
        store.put("/etc/passwd", b"x")


def test_rejects_traversal_key(store: LocalDiskStorage) -> None:
    with pytest.raises(ValueError):
        store.put("../escape.txt", b"x")


async def test_atomic_write_does_not_leave_tmp_on_success(
    store: LocalDiskStorage, tmp_path: Path
) -> None:
    store.put("atomic.bin", b"data")
    leftover = list(tmp_path.glob("**/.*atomic.bin.*.tmp"))
    assert leftover == []


async def test_writes_handle_binary_payloads(store: LocalDiskStorage) -> None:
    payload = bytes(range(256))
    store.put("blob.bin", payload)
    assert store.get("blob.bin") == payload
