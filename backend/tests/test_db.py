from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal


async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "0.1.0"
    assert body["db"] is True


async def test_db_select_one_runs() -> None:
    async with SessionLocal() as session:
        result = (await session.execute(text("SELECT 1 AS one"))).scalar_one()
    assert result == 1


def test_alembic_has_at_least_one_revision() -> None:
    versions_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    revisions = [p for p in versions_dir.glob("*.py") if not p.name.startswith("_")]
    assert revisions, "expected at least one Alembic revision"


@pytest.mark.parametrize(
    "name",
    ["script.py.mako", "env.py"],
)
def test_alembic_layout_files_exist(name: str) -> None:
    base = Path(__file__).resolve().parents[1] / "migrations"
    assert (base / name).is_file()
