"""Unit tests for `app.services.extraction`."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.extraction import ExtractionError, extract

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_pdf_returns_text_content() -> None:
    content = (FIXTURES / "sample.pdf").read_bytes()
    text = extract("sample.pdf", content)

    assert "Hello, world from PDF" in text
    assert "second line" in text


def test_extract_docx_returns_text_content() -> None:
    content = (FIXTURES / "sample.docx").read_bytes()
    text = extract("sample.docx", content)

    assert "Hello, world from DOCX" in text
    assert "second paragraph" in text


def test_extract_txt_round_trips() -> None:
    content = (FIXTURES / "sample.txt").read_bytes()
    text = extract("sample.txt", content)
    assert text == content.decode("utf-8")
    assert "Hello, world from TXT" in text


def test_extract_empty_txt_returns_empty_string() -> None:
    text = extract("empty.txt", b"")
    assert text == ""


def test_extract_unsupported_extension_raises() -> None:
    with pytest.raises(ExtractionError) as excinfo:
        extract("weird.xyz", b"x")
    assert "unsupported" in excinfo.value.reason


def test_extract_corrupted_pdf_raises() -> None:
    bogus = b"\x00\x01\x02\x03this is not a valid pdf"
    with pytest.raises(ExtractionError) as excinfo:
        extract("garbage.pdf", bogus)
    assert "pdf parse failed" in excinfo.value.reason


def test_extract_corrupted_docx_raises() -> None:
    bogus = b"not a real docx file"
    with pytest.raises(ExtractionError) as excinfo:
        extract("garbage.docx", bogus)
    assert "docx parse failed" in excinfo.value.reason


@pytest.mark.parametrize("filename", ["x.PDF", "x.Pdf", "x.DOCX", "x.TXT"])
def test_extract_is_case_insensitive(filename: str) -> None:
    suffix = filename.rsplit(".", 1)[-1].lower()
    if suffix == "pdf":
        content = (FIXTURES / "sample.pdf").read_bytes()
    elif suffix == "docx":
        content = (FIXTURES / "sample.docx").read_bytes()
    else:
        content = (FIXTURES / "sample.txt").read_bytes()
    text = extract(filename, content)
    assert text  # non-empty


def test_extract_with_no_extension_raises() -> None:
    with pytest.raises(ExtractionError):
        extract("no-extension", b"anything")
