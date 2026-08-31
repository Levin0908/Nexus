"""Text extraction.

Given a filename and raw file bytes, pull out the plain text. Dispatch by
extension. Unsupported / corrupted files raise `ExtractionError` with a
human-readable `.reason` the caller can log or surface to the user.

Supported for Day 9:
- `.pdf`  — via pypdf
- `.docx` — via python-docx
- `.txt`  — stdlib UTF-8 decode with replacement
"""

from __future__ import annotations

import io
from pathlib import Path

import docx
import pypdf


class ExtractionError(Exception):
    """Raised when text extraction cannot be performed.

    `reason` is a short, human-readable label — useful for logs and for
    surfacing to the API consumer (e.g. as `status=failed` with the reason
    in a future audit column).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _extract_pdf(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"pdf parse failed: {exc}") from exc

    try:
        pages_text = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ExtractionError(f"pdf page extract failed: {exc}") from exc

    return "\n".join(pages_text)


def _extract_docx(content: bytes) -> str:
    try:
        document = docx.Document(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"docx parse failed: {exc}") from exc

    try:
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise ExtractionError(f"docx paragraph extract failed: {exc}") from exc


def _extract_txt(content: bytes) -> str:
    return content.decode("utf-8", errors="replace")


_DISPATCH = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_txt,
}


def extract(filename: str, content: bytes) -> str:
    """Return plain text from the given filename + bytes.

    Dispatches by lowercased extension. Raises `ExtractionError("unsupported")`
    for unknown types. Returns `""` for an empty TXT (a valid 0-byte file).
    """
    suffix = Path(filename).suffix.lower()
    impl = _DISPATCH.get(suffix)
    if impl is None:
        raise ExtractionError(f"unsupported extension: {suffix!r}")
    return impl(content)
