from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.document import DocumentSearchHit
from app.services.search import search_documents

router = APIRouter()


@router.get("", response_model=list[DocumentSearchHit])
async def search(
    current_user: CurrentUser,
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=256, description="Search terms")],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[DocumentSearchHit]:
    """Full-text search across the current user's documents.

    Uses Postgres `to_tsvector`/`plainto_tsquery` with the English config
    and a GIN index. Always scoped to the calling user; other users'
    documents never appear.

    - `q` — 1-256 chars. Special chars are safe (`plainto_tsquery` treats
       input as plain text, so punctuation and operators don't crash).
    - `limit` — 1-100, default 20. Ordered by `ts_rank` DESC.
    """
    return await search_documents(db, owner=current_user, query=q, limit=limit)
