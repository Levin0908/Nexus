"""Generate the binary fixture files used by tests/test_extraction.py.

Run from the `backend/` directory with the project venv active:

    uv run python scripts/generate_fixtures.py

This is a one-time setup step. The output files in `tests/fixtures/` are
committed to the repo and loaded at test time — no runtime regeneration.
"""

from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

SAMPLE_TXT = "Hello, world from TXT.\nThis is the second line.\n"
SAMPLE_DOCX_PARAGRAPHS = [
    "Hello, world from DOCX.",
    "This is the second paragraph.",
    "Third paragraph for good measure.",
]
SAMPLE_PDF_LINES = [
    "Hello, world from PDF.",
    "This is the second line on the PDF page.",
    "And a third one too.",
]


def write_sample_txt(out_dir: Path) -> Path:
    path = out_dir / "sample.txt"
    path.write_text(SAMPLE_TXT, encoding="utf-8")
    return path


def write_sample_docx(out_dir: Path) -> Path:
    path = out_dir / "sample.docx"
    doc = Document()
    for text in SAMPLE_DOCX_PARAGRAPHS:
        doc.add_paragraph(text)
    buf = io.BytesIO()
    doc.save(buf)
    path.write_bytes(buf.getvalue())
    return path


def write_sample_pdf(out_dir: Path) -> Path:
    path = out_dir / "sample.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 720
    for line in SAMPLE_PDF_LINES:
        c.drawString(72, y, line)
        y -= 20
    c.showPage()
    c.save()
    return path


def main() -> None:
    out_dir = Path(__file__).parent.parent / "tests" / "fixtures"
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in (write_sample_txt(out_dir), write_sample_docx(out_dir), write_sample_pdf(out_dir)):
        size = path.stat().st_size
        print(f"wrote {path.relative_to(out_dir.parent.parent)} ({size} bytes)")


if __name__ == "__main__":
    main()
