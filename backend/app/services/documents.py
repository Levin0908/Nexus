"""Document service: business logic for the upload pipeline.

Routes stay thin: parse inputs, call a service, translate domain errors to
HTTP. This module is where the write+hash+insert logic actually lives so it
can be unit-tested without going through FastAPI.
"""

from __future__ import annotations

import hashlib
import tempfile
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.storage import Storage

_FILENAME_MAX_LEN = 255
_READ_CHUNK = 64 * 1024


class FileTooLargeError(Exception):
    """Raised when an upload exceeds the configured byte cap.

    Carries the rejected size so the route can include it in the 413 response.
    """

    def __init__(self, size: int) -> None:
        super().__init__(f"file too large: {size} bytes")
        self.size = size


def sanitize_filename(name: str | None) -> str:
    """Strip path components and null bytes; cap length; never return empty.

    Defends against `Content-Disposition` filenames like `../etc/passwd` or
    `evil\x00.txt`. The result is what we display and what we store as
    `documents.filename`. It is NOT used to construct a storage key (that's
    done by `sanitize_ext` + a server-generated UUID).
    """
    if not name:
        return "upload.bin"
    cleaned = name.replace("\x00", "").strip()
    cleaned = Path(cleaned).name  # strip any directory components
    if not cleaned or cleaned in {".", ".."}:
        return "upload.bin"
    if len(cleaned) > _FILENAME_MAX_LEN:
        stem = Path(cleaned).stem[: _FILENAME_MAX_LEN - 8]
        suffix = Path(cleaned).suffix[:8]
        cleaned = (stem + suffix)[:_FILENAME_MAX_LEN]
    return cleaned


def sanitize_ext(name: str | None) -> str:
    """Return a lowercased file extension including the leading dot, or `.bin`.

    Rejects suffixes containing non-alphanumeric characters or longer than 8
    chars. Combined with `Path(name).suffix` this prevents a caller from
    sneaking weird characters into the storage path.
    """
    if not name:
        return ".bin"
    suffix = Path(name).suffix.lower()
    if not suffix or len(suffix) > 8:
        return ".bin"
    if not suffix.startswith("."):
        return ".bin"
    body = suffix[1:]
    if not body or not body.isalnum():
        return ".bin"
    return suffix


async def create_document_from_upload(
    *,
    db: AsyncSession,
    storage: Storage,
    owner: User,
    upload: UploadFile,
) -> Document:
    """Persist a freshly-uploaded file as a new `Document` row.

    Streams the upload in 64 KiB chunks, hashing + size-checking each one,
    then writes to storage and inserts the row. The file never lives entirely
    in memory: it passes through a `SpooledTemporaryFile` (1 MiB in memory,
    the rest on disk), then from the spool to storage via `put_file_obj`.

    If the cap is exceeded mid-stream, raises `FileTooLargeError` and no
    file is written. If the DB insert fails after the file lands, the file
    is deleted before the exception propagates.
    """
    doc_id = uuid.uuid4()
    safe_filename = sanitize_filename(upload.filename)
    ext = sanitize_ext(upload.filename)
    key = f"{owner.id}/{doc_id}{ext}"

    hasher = hashlib.sha256()
    size = 0
    spool = tempfile.SpooledTemporaryFile(max_size=1_048_576, mode="w+b")
    try:
        while True:
            chunk = await upload.read(_READ_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.storage_max_file_size_bytes:
                raise FileTooLargeError(size)
            hasher.update(chunk)
            spool.write(chunk)
    finally:
        spool.seek(0)

    storage.put_file_obj(key, spool)
    spool.close()

    document = Document(
        id=doc_id,
        owner_id=owner.id,
        filename=safe_filename,
        mime_type=upload.content_type or "application/octet-stream",
        size_bytes=size,
        storage_path=key,
        sha256=hasher.hexdigest(),
        status=DocumentStatus.READY,
    )
    db.add(document)
    try:
        await db.commit()
    except IntegrityError:
        storage.delete(key)
        await db.rollback()
        raise

    await db.refresh(document)
    return document
