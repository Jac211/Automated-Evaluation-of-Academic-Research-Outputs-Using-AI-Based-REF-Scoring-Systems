"""Text extraction, reference stripping and segmentation."""
from __future__ import annotations

import io
import re

from pypdf import PdfReader

_REFERENCE_HEADING = re.compile(
    r"^\s*(?:\d+\.?\s*)?(references|bibliography|works cited|literature cited|reference list)\s*:?\s*$",
    flags=re.IGNORECASE | re.MULTILINE,
)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from every page of a PDF, keeping line breaks."""
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = (page.extract_text() for page in reader.pages)
    return "\n".join(text for text in pages if text)


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode a plain text file, tolerating stray non-UTF-8 bytes."""
    return file_bytes.decode("utf-8", errors="ignore")


def extract_text(file_name: str, file_bytes: bytes) -> str:
    if file_name.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    return extract_text_from_txt(file_bytes)


def strip_references(text: str) -> str:
    """Drop everything from the last "References"-style heading onwards.

    Only headings in the second half of the text count, so a table of contents or an
    early mention can't remove the body of the paper.
    """
    matches = [m for m in _REFERENCE_HEADING.finditer(text) if m.start() >= len(text) / 2]
    return text[: matches[-1].start()] if matches else text


def count_words(text: str) -> int:
    return len(text.split())


def segment_text(text: str, segment_words: int) -> list[str]:
    """Split text into chunks of up to `segment_words` words, keeping the original spacing."""
    spans = [m.span() for m in re.finditer(r"\S+", text)]
    return [
        text[spans[i][0]: spans[min(i + segment_words, len(spans)) - 1][1]]
        for i in range(0, len(spans), segment_words)
    ]
