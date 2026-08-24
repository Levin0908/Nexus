from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str | bool]:
    db_ok = True
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok",
        "env": "development" if settings.debug else "production",
        "version": settings.version,
        "db": db_ok,
    }
