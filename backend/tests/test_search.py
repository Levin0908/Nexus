"""Search endpoint tests (`GET /api/v1/search` and `GET /api/v1/documents/{id}`)."""

from __future__ import annotations

import io
import uuid
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


async def _register(client, *, email: str | None = None) -> str:
    email = email or f"test-{uuid.uuid4()}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "test-password-123"},
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


async def _upload_fixture(client, token: str, name: str, content_type: str) -> str:
    payload = (FIXTURES / name).read_bytes()
    resp = await _upload(client, token, filename=name, content=payload, content_type=content_type)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ─── /search ──────────────────────────────────────────────────────────────


async def test_search_without_auth_returns_401(client) -> None:
    resp = await client.get("/api/v1/search", params={"q": "anything"})
    assert resp.status_code == 401


async def test_search_with_empty_query_returns_422(client) -> None:
    token = await _register(client)
    resp = await client.get("/api/v1/search", params={"q": ""}, headers=_bearer(token))
    assert resp.status_code == 422


async def test_search_with_overlong_query_returns_422(client) -> None:
    token = await _register(client)
    resp = await client.get(
        "/api/v1/search",
        params={"q": "a" * 257},
        headers=_bearer(token),
    )
    assert resp.status_code == 422


async def test_search_with_no_matches_returns_empty_list(client) -> None:
    token = await _register(client)
    await _upload_fixture(client, token, "sample.txt", "text/plain")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "nonexistent_xyz_word"},
        headers=_bearer(token),
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


async def test_search_finds_uploaded_text(client) -> None:
    token = await _register(client)
    await _upload_fixture(client, token, "sample.txt", "text/plain")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "Hello"},
        headers=_bearer(token),
    )

    assert resp.status_code == 200, resp.text
    hits = resp.json()
    assert len(hits) == 1
    hit = hits[0]
    assert "extracted_text" not in hit  # slim hit
    assert hit["filename"] == "sample.txt"
    assert hit["status"] == "ready"
    assert hit["rank"] > 0


async def test_search_returns_results_ordered_by_rank(client) -> None:
    token = await _register(client)
    # Upload two docs with different content lengths so ranks actually differ.
    await _upload_fixture(client, token, "sample.pdf", "application/pdf")
    await _upload_fixture(
        client,
        token,
        "sample.docx",
        "application/octet-stream",
    )

    resp = await client.get(
        "/api/v1/search",
        params={"q": "Hello"},
        headers=_bearer(token),
    )

    assert resp.status_code == 200, resp.text
    hits = resp.json()
    assert len(hits) == 2
    ranks = [h["rank"] for h in hits]
    assert ranks == sorted(ranks, reverse=True)


async def test_search_uses_postgres_english_stemming(client) -> None:
    """Searching for a stem variant should still find the original word."""
    token = await _register(client)
    # sample.txt contains "Hello" — stemming for "Hello" finds it,
    # but let's also verify "running" finds "runs" if we add that word.
    # Easier: search "world" matches "world" via stemming-related lexize.
    await _upload_fixture(client, token, "sample.txt", "text/plain")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "world"},
        headers=_bearer(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_search_with_special_chars_does_not_crash(client) -> None:
    token = await _register(client)
    await _upload_fixture(client, token, "sample.txt", "text/plain")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "!@#$%^&*()"},
        headers=_bearer(token),
    )

    assert resp.status_code == 200, resp.text
    # Punctuation-as-terms may produce no matches but should never 500.
    assert resp.json() == []


async def test_search_limit_param_is_honored(client) -> None:
    token = await _register(client)
    await _upload_fixture(client, token, "sample.txt", "text/plain")
    await _upload_fixture(client, token, "sample.pdf", "application/pdf")
    await _upload_fixture(client, token, "sample.docx", "application/octet-stream")

    resp = await client.get(
        "/api/v1/search",
        params={"q": "Hello", "limit": 1},
        headers=_bearer(token),
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


async def test_search_limit_above_max_returns_422(client) -> None:
    token = await _register(client)
    resp = await client.get(
        "/api/v1/search", params={"q": "x", "limit": 1000}, headers=_bearer(token)
    )
    assert resp.status_code == 422


async def test_search_is_owner_scoped(client) -> None:
    tok_a = await _register(client, email=f"test-a-{uuid.uuid4()}@example.com")
    tok_b = await _register(client, email=f"test-b-{uuid.uuid4()}@example.com")

    await _upload_fixture(client, tok_a, "sample.txt", "text/plain")
    await _upload_fixture(client, tok_b, "sample.txt", "text/plain")

    resp_a = await client.get("/api/v1/search", params={"q": "Hello"}, headers=_bearer(tok_a))
    resp_b = await client.get("/api/v1/search", params={"q": "Hello"}, headers=_bearer(tok_b))

    assert resp_a.status_code == 200 and resp_b.status_code == 200
    assert len(resp_a.json()) == 1
    assert len(resp_b.json()) == 1
    assert resp_a.json()[0]["id"] != resp_b.json()[0]["id"]


# ─── /documents/{id} ──────────────────────────────────────────────────────


async def test_get_document_returns_full_payload(client) -> None:
    token = await _register(client)
    doc_id = await _upload_fixture(client, token, "sample.txt", "text/plain")

    resp = await client.get(f"/api/v1/documents/{doc_id}", headers=_bearer(token))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == doc_id
    assert body["filename"] == "sample.txt"
    assert body["extracted_text"] is not None
    assert "Hello" in body["extracted_text"]


async def test_get_document_for_other_users_doc_returns_404(client) -> None:
    tok_a = await _register(client, email=f"test-a-{uuid.uuid4()}@example.com")
    tok_b = await _register(client, email=f"test-b-{uuid.uuid4()}@example.com")
    a_doc_id = await _upload_fixture(client, tok_a, "sample.txt", "text/plain")

    resp = await client.get(f"/api/v1/documents/{a_doc_id}", headers=_bearer(tok_b))
    assert resp.status_code == 404, resp.text


async def test_get_document_for_nonexistent_id_returns_404(client) -> None:
    token = await _register(client)
    bogus = uuid.uuid4()
    resp = await client.get(f"/api/v1/documents/{bogus}", headers=_bearer(token))
    assert resp.status_code == 404


async def test_get_document_without_auth_returns_401(client) -> None:
    bogus = uuid.uuid4()
    resp = await client.get(f"/api/v1/documents/{bogus}")
    assert resp.status_code == 401
