from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentStatus(StrEnum):
    """Lifecycle of a Document.

    - uploading: row exists, the file is in flight (Day 8 upload endpoint).
    - ready:     file is on disk, hash verified, ready for text extraction.
    - failed:    ingestion failed; file may or may not be on disk.
    """

    UPLOADING = "uploading"
    READY = "ready"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        SAEnum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        server_default=text("'uploading'"),
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('english', COALESCE(extracted_text, ''))",
            persisted=True,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index("ix_documents_owner_id", "owner_id"),
        UniqueConstraint(
            "owner_id",
            "sha256",
            name="uq_documents_owner_sha256",
        ),
        Index(
            "ix_documents_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} owner={self.owner_id} "
            f"filename={self.filename!r} status={self.status}>"
        )
