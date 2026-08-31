from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.api.deps import CurrentUser, DbSession, StorageDep
from app.core.config import settings
from app.schemas.document import DocumentPublic
from app.services.documents import FileTooLargeError, create_document_from_upload

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
