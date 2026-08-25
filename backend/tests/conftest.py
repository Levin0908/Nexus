"""Pytest fixtures shared across tests."""

import httpx
import pytest_asyncio

from app.db.session import SessionLocal, engine
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


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_test_users() -> None:
    """Wipe any user rows created by tests after each test runs.

    Tests use the `test-*@example.com` email pattern. After the test, we delete
    any matching rows so reruns and ordering don't collide.
    """
    yield
    from sqlalchemy import delete  # local import keeps top of file clean

    from app.models.user import User

    async with SessionLocal() as session:
        await session.execute(delete(User).where(User.email.like("test-%@example.com")))
        await session.commit()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine_at_session_end() -> None:
    """Release asyncpg connections when the test session ends."""
    yield
    await engine.dispose()
