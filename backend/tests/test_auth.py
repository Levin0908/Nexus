from __future__ import annotations

import uuid

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.user import User


def _make_email() -> str:
    return f"test-{uuid.uuid4()}@example.com"


async def _register(client: AsyncClient, *, email: str | None = None) -> dict:
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": email or _make_email(),
            "password": "hunter2hunter2",
        },
    )


async def test_register_happy_path(client: AsyncClient) -> None:
    email = _make_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_access_ttl_minutes * 60
    access = body["access_token"]
    refresh = body["refresh_token"]
    assert isinstance(access, str) and access.count(".") == 2
    assert isinstance(refresh, str) and refresh.count(".") == 2


async def test_register_duplicate_email_returns_409(client: AsyncClient) -> None:
    email = _make_email()
    first = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "different-pw-1234"},
    )
    assert second.status_code == 409
    assert second.json() == {"detail": "email already registered"}


async def test_register_invalid_email_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "hunter2hunter2"},
    )
    assert response.status_code == 422


async def test_register_too_short_password_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": _make_email(), "password": "short"},
    )
    assert response.status_code == 422


async def test_register_too_long_password_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": _make_email(), "password": "x" * 129},
    )
    assert response.status_code == 422


async def test_register_lowercases_email(client: AsyncClient) -> None:
    mixed = f"Test-{uuid.uuid4()}@Example.COM"
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": mixed, "password": "hunter2hunter2"},
    )
    assert response.status_code == 201

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == mixed.lower()))
        user = result.scalar_one_or_none()
    assert user is not None
    assert user.email == mixed.lower()


async def test_login_happy_path(client: AsyncClient) -> None:
    email = _make_email()
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert register.status_code == 201

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.jwt_access_ttl_minutes * 60
    assert body["access_token"].count(".") == 2
    assert body["refresh_token"].count(".") == 2


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    email = _make_email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password-123"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


async def test_login_unknown_email_returns_401_with_no_enumeration_leak(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": _make_email(), "password": "hunter2hunter2"},
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "invalid credentials"}


async def test_login_disabled_user_returns_403(client: AsyncClient) -> None:
    email = _make_email()
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "account disabled"}


async def test_access_token_has_correct_claims(client: AsyncClient) -> None:
    email = _make_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    assert response.status_code == 201
    access = response.json()["access_token"]

    claims = decode_token(access, expected_type="access")
    assert claims["type"] == "access"
    assert claims["sub"]
    assert "exp" in claims
    assert "iat" in claims
    assert "jti" in claims


async def test_refresh_token_has_correct_claims_and_longer_expiry(
    client: AsyncClient,
) -> None:
    email = _make_email()
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    body = response.json()
    access = body["access_token"]
    refresh = body["refresh_token"]

    access_claims = decode_token(access, expected_type="access")
    refresh_claims = decode_token(refresh, expected_type="refresh")

    assert refresh_claims["type"] == "refresh"
    refresh_life = refresh_claims["exp"] - refresh_claims["iat"]
    access_life = access_claims["exp"] - access_claims["iat"]
    assert refresh_life > access_life


async def test_decode_rejects_tampered_signature(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": _make_email(), "password": "hunter2hunter2"},
    )
    access = response.json()["access_token"]

    head, payload, signature = access.split(".")
    flipped = "A" if signature[-1] != "A" else "B"
    tampered = ".".join([head, payload, signature[:-1] + flipped])

    with pytest.raises(jwt.PyJWTError):
        decode_token(tampered, expected_type="access")


# ---------------------------------------------------------------------------
# Day 6 — protected routes + token refresh
# ---------------------------------------------------------------------------


async def _register_and_get_tokens(client: AsyncClient) -> tuple[str, str]:
    """Helper: register a fresh user, return (access_token, refresh_token)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": _make_email(), "password": "hunter2hunter2"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body["refresh_token"]


async def test_me_with_valid_access_token(client: AsyncClient) -> None:
    access, _ = await _register_and_get_tokens(client)
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert "email" in body
    assert body["is_active"] is True
    assert "created_at" in body


async def test_me_without_authorization_header(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_me_with_wrong_scheme(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401


async def test_me_with_garbage_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401


async def test_me_with_refresh_token_instead_of_access(client: AsyncClient) -> None:
    _, refresh = await _register_and_get_tokens(client)
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh}"},
    )
    assert response.status_code == 401


async def test_me_with_token_signed_by_wrong_secret(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    access, _ = await _register_and_get_tokens(client)
    monkeypatch.setattr(settings, "jwt_secret_key", "an-entirely-different-secret")
    monkeypatch.setattr("app.core.security._jwt_secret_cache", None)
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 401


async def test_me_with_disabled_user_returns_403(client: AsyncClient) -> None:
    email = _make_email()
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "hunter2hunter2"},
    )
    access = register.json()["access_token"]

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert response.status_code == 403
    assert response.json() == {"detail": "account disabled"}


async def test_refresh_with_valid_refresh_token(client: AsyncClient) -> None:
    _, refresh = await _register_and_get_tokens(client)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    new_access = body["access_token"]
    assert new_access.count(".") == 2

    claims = decode_token(new_access, expected_type="access")
    assert claims["type"] == "access"


async def test_refresh_with_access_token_rejected(client: AsyncClient) -> None:
    access, _ = await _register_and_get_tokens(client)
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access},
    )
    assert response.status_code == 401


async def test_refresh_with_garbage_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-real-token"},
    )
    assert response.status_code == 401
