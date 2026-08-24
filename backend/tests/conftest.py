"""Pytest fixtures shared across tests."""

import httpx
import pytest_asyncio

from app.main import app


@pytest_asyncio.fixture
async def client() -> httpx.AsyncClient:
    """Async HTTP client that drives the FastAPI app on the *current* loop.

    Using httpx.AsyncClient with ASGITransport (instead of FastAPI's sync
    TestClient) means the request runs on the same event loop pytest-asyncio
    sets up. That way SQLAlchemy's AsyncEngine pool (which binds to the first
    loop it sees) stays consistent across tests.
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
