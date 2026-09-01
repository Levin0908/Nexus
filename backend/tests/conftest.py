"""Pytest fixtures shared across tests."""

from pathlib import Path

import httpx
import pytest_asyncio

from app.api.deps import get_storage
from app.db.session import SessionLocal, engine
from app.main import app
from app.storage.local import LocalDiskStorage


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
async def test_storage(tmp_path: Path):
    """Per-test isolated Storage instance.

    Autouse so every test gets a fresh tmp dir for file writes (no real
    `./var/documents` pollution). The yielded value lets tests that need to
    inspect on-disk state do so without re-resolving the override.
    """
    storage = LocalDiskStorage(tmp_path)
    app.dependency_overrides[get_storage] = lambda: storage
    yield storage
    app.dependency_overrides.pop(get_storage, None)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_test_users() -> None:
    """Wipe test users (and their docs via ON DELETE CASCADE) after each test runs.

    Tests use the `test-%@example.com` email pattern. After the test, we delete
    any matching rows so reruns and ordering don't collide. Documents owned by
    these users cascade-delete automatically via the FK on `documents.owner_id`
    — see migration `73515ccace6e_create_documents_table.py`. We no longer run
    a separate `_cleanup_test_documents` because an unfiltered `delete(Document)`
    would erase any rows a live uvicorn instance had created, since pytest and
    dev share the same Postgres database.
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
