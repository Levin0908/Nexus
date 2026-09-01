from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession, StorageDep
from app.core.config import settings
from app.schemas.document import DocumentPublic
from app.services.documents import FileTooLargeError, create_document_from_upload
from app.services.search import get_document_for_owner

router = APIRouter()


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=DocumentPublic,
    responses={
        401: {"description": "Missing or invalid bearer token"},
        413: {"description": "File exceeds the configured size cap"},
        422: {"description": "Multipart payload is malformed"},
    },
)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document to upload (PDF, DOCX, TXT, etc.)")],
    current_user: CurrentUser,
    db: DbSession,
    storage: StorageDep,
) -> DocumentPublic:
    """Upload a new document for the current user.

    The file is streamed to disk, hashed (SHA-256), and a `Document` row is
    inserted with `status=ready`. Bytes never accumulate fully in memory;
    the size cap is enforced mid-stream.
    """
    try:
        document = await create_document_from_upload(
            db=db,
            storage=storage,
            owner=current_user,
            upload=file,
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=(
                f"file exceeds the configured cap of "
                f"{settings.storage_max_file_size_bytes} bytes (got {exc.size})"
            ),
        ) from None

    return DocumentPublic.model_validate(document)


@router.get(
    "/{document_id}",
    response_model=DocumentPublic,
    responses={404: {"description": "Document not found or not owned by caller"}},
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> DocumentPublic:
    """Retrieve a single document (including extracted_text) by id.

    Owner-scoped: returns 404 for documents owned by other users so the API
    doesn't leak existence.
    """
    document = await get_document_for_owner(db, owner=current_user, document_id=document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="document not found",
        )
    return DocumentPublic.model_validate(document)
