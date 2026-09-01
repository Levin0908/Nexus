"""Search service.

Owns the Postgres FTS query for `documents.search_vector`. Returns
`DocumentSearchHit` rows ordered by ts_rank DESC, always scoped to the
supplied owner.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentSearchHit


async def search_documents(
    db: AsyncSession,
    *,
    owner: User,
    query: str,
    limit: int,
) -> list[DocumentSearchHit]:
    """Search the calling user's documents via Postgres full-text search.

    Uses `plainto_tsquery` so user input is treated as plain terms — no special
    operator parsing, no crash on punctuation. Matches via the @@ operator on
    the `search_vector` GIN-indexed column; orders by `ts_rank` DESC; always
    filters by `owner_id` so users never see each other's documents.
    """
    ts_query = func.plainto_tsquery("english", query)

    stmt = (
        select(
            Document.id,
            Document.owner_id,
            Document.filename,
            Document.mime_type,
            Document.size_bytes,
            Document.storage_path,
            Document.sha256,
            Document.status,
            Document.created_at,
            Document.updated_at,
            func.ts_rank(Document.search_vector, ts_query).label("rank"),
        )
        .where(
            Document.owner_id == owner.id,
            Document.search_vector.op("@@")(ts_query),
        )
        .order_by(func.ts_rank(Document.search_vector, ts_query).desc())
        .limit(limit)
    )

    rows = (await db.execute(stmt)).all()
    return [DocumentSearchHit.model_validate(row._mapping) for row in rows]


async def get_document_for_owner(
    db: AsyncSession,
    *,
    owner: User,
    document_id: uuid.UUID,
) -> Document | None:
    """Fetch a document row only if it belongs to `owner`. Returns None otherwise.

    Used by `GET /documents/{id}` so cross-user lookups return None (route
    then maps to 404, avoiding existence-leak via 403).
    """
    document = await db.get(Document, document_id)
    if document is None or document.owner_id != owner.id:
        return None
    return document
