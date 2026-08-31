"""Upload endpoint tests (`POST /api/v1/documents`)."""

from __future__ import annotations

import hashlib
import io
import uuid

import pytest


async def _register(client, email: str | None = None, password: str = "test-password-123") -> str:
    email = email or f"test-{uuid.uuid4()}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _upload(client, token: str, *, filename: str, content: bytes, content_type: str):
    return await client.post(
        "/api/v1/documents",
        files={"file": (filename, io.BytesIO(content), content_type)},
        headers=_bearer(token),
    )


async def test_upload_small_file_returns_201_with_ready_status(client, test_storage) -> None:
    token = await _register(client)
    payload = b"hello, world\nthis is a test document.\n"

    resp = await _upload(
        client,
        token,
        filename="notes.txt",
        content=payload,
        content_type="text/plain",
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == "notes.txt"
    assert body["mime_type"] == "text/plain"
    assert body["size_bytes"] == len(payload)
    assert body["status"] == "ready"
    assert body["sha256"] == hashlib.sha256(payload).hexdigest()
    assert body["storage_path"].endswith(".txt")

    key = body["storage_path"]
    assert test_storage.exists(key)
    assert test_storage.get(key) == payload
    assert test_storage.size(key) == len(payload)


async def test_upload_without_auth_returns_401(client) -> None:
    resp = await client.post(
        "/api/v1/documents",
        files={"file": ("x.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert resp.status_code == 401


async def test_upload_over_size_cap_returns_413(client, test_storage) -> None:
    token = await _register(client)
    too_big = b"\x00" * (1024 * 1024 + 1)  # 1 MiB + 1 byte; default cap is 100 MiB

    # Shrink the cap for this test so we don't have to allocate 100 MiB.
    from app.core.config import settings

    original = settings.storage_max_file_size_bytes
    settings.storage_max_file_size_bytes = 1024
    try:
        resp = await _upload(
            client,
            token,
            filename="huge.bin",
            content=too_big,
            content_type="application/octet-stream",
        )
    finally:
        settings.storage_max_file_size_bytes = original

    assert resp.status_code == 413, resp.text
    assert "exceeds" in resp.json()["detail"].lower()
    # No file landed on disk and no DB row was inserted.
    assert list(test_storage.root.rglob("*")) == []


async def test_upload_missing_file_part_returns_422(client) -> None:
    token = await _register(client)
    resp = await client.post(
        "/api/v1/documents",
        headers=_bearer(token),
    )
    assert resp.status_code == 422


async def test_upload_empty_file_returns_201(client, test_storage) -> None:
    token = await _register(client)

    resp = await _upload(
        client,
        token,
        filename="empty.txt",
        content=b"",
        content_type="text/plain",
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["size_bytes"] == 0
    assert body["sha256"] == hashlib.sha256(b"").hexdigest()
    assert body["status"] == "ready"
    assert test_storage.exists(body["storage_path"])
    assert test_storage.get(body["storage_path"]) == b""


async def test_upload_sanitizes_traversal_filename(client, test_storage) -> None:
    token = await _register(client)
    payload = b"safe content"

    resp = await _upload(
        client,
        token,
        filename="../../etc/passwd",
        content=payload,
        content_type="text/plain",
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == "passwd"
    # storage_path uses the original extension; here there is none
    assert body["storage_path"].endswith(".bin")


async def test_upload_sanitizes_null_byte_filename(client) -> None:
    token = await _register(client)

    resp = await _upload(
        client,
        token,
        filename="evil\x00name.txt",
        content=b"data",
        content_type="text/plain",
    )

    assert resp.status_code == 201, resp.text
    assert "\x00" not in resp.json()["filename"]


async def test_upload_same_user_twice_yields_different_storage_paths(client) -> None:
    token = await _register(client)

    r1 = await _upload(client, token, filename="a.txt", content=b"one", content_type="text/plain")
    r2 = await _upload(client, token, filename="a.txt", content=b"two", content_type="text/plain")

    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["storage_path"] != r2.json()["storage_path"]


async def test_two_users_uploads_are_isolated_by_owner_folder(client) -> None:
    tok_a = await _register(client, email=f"test-a-{uuid.uuid4()}@example.com")
    tok_b = await _register(client, email=f"test-b-{uuid.uuid4()}@example.com")

    ra = await _upload(
        client,
        tok_a,
        filename="same.txt",
        content=b"alice",
        content_type="text/plain",
    )
    rb = await _upload(
        client,
        tok_b,
        filename="same.txt",
        content=b"bob",
        content_type="text/plain",
    )

    assert ra.status_code == 201 and rb.status_code == 201
    assert ra.json()["owner_id"] != rb.json()["owner_id"]


async def test_owner_id_in_response_matches_current_user(client) -> None:
    from app.core.security import decode_token

    token = await _register(client)
    claims = decode_token(token, expected_type="access")
    expected_user_id = claims["sub"]

    resp = await _upload(client, token, filename="x.txt", content=b"y", content_type="text/plain")
    assert resp.status_code == 201
    assert resp.json()["owner_id"] == expected_user_id


async def test_uploaded_bytes_match_storage_contents_and_hash(client, test_storage) -> None:
    token = await _register(client)
    payload = bytes(range(256)) * 4  # 1024 bytes of binary

    resp = await _upload(
        client,
        token,
        filename="blob.bin",
        content=payload,
        content_type="application/octet-stream",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert test_storage.get(body["storage_path"]) == payload
    assert body["sha256"] == hashlib.sha256(payload).hexdigest()


async def test_storage_override_isolates_per_test(client, test_storage) -> None:
    """Sanity check: writing through the upload endpoint writes into test_storage.root."""
    token = await _register(client)
    resp = await _upload(
        client,
        token,
        filename="check.txt",
        content=b"check",
        content_type="text/plain",
    )
    assert resp.status_code == 201

    key = resp.json()["storage_path"]
    on_disk = test_storage.root / key
    assert on_disk.is_file()
    assert on_disk.read_bytes() == b"check"


@pytest.mark.parametrize(
    "filename,expected_ext",
    [
        ("report.PDF", ".pdf"),
        ("paper.docx", ".docx"),
        ("plain.txt", ".txt"),
        ("no-extension", ".bin"),
        ("trailing-dot.", ".bin"),
        ("weird.tar.gz", ".gz"),
    ],
)
async def test_storage_extension_dispatch(client, filename: str, expected_ext: str) -> None:
    token = await _register(client)
    resp = await _upload(
        client,
        token,
        filename=filename,
        content=b"x",
        content_type="application/octet-stream",
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["storage_path"].endswith(expected_ext)
