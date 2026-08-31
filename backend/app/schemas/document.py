from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    sha256: str
    status: DocumentStatus
    extracted_text: str | None
    created_at: datetime
    updated_at: datetime
