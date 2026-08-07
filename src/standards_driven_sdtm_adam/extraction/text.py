"""Local document text extraction for standards evidence search."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class TextBlock:
    """Searchable text block with verified source location metadata."""

    text: str
    section: str | None = None
    page: int | None = None


class TextExtractionError(RuntimeError):
    """Raised when local text extraction fails."""


def extract_text_blocks(path: Path) -> list[TextBlock]:
    """Extract searchable text blocks from a local standards document."""

    if not path.exists():
        raise FileNotFoundError(path)

    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _extract_plain_text_blocks(path)
    if suffix == ".pdf":
        return _extract_pdf_blocks(path)

    raise TextExtractionError(f"Unsupported standards document type: {suffix}")


def _extract_plain_text_blocks(path: Path) -> list[TextBlock]:
    content = path.read_text(encoding="utf-8")
    blocks: list[TextBlock] = []
    section: str | None = None
    page: int | None = None
    paragraph: list[str] = []

    def flush() -> None:
        nonlocal paragraph
        text = " ".join(line.strip() for line in paragraph if line.strip())
        if text:
            blocks.append(TextBlock(text=text, section=section, page=page))
        paragraph = []

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            continue

        page_match = re.fullmatch(r"\[page\s+([0-9]+)\]", line, flags=re.IGNORECASE)
        if page_match:
            flush()
            page = int(page_match.group(1))
            continue

        heading_match = re.match(r"^(?:#{1,6}\s+|section\s+)(.+)$", line, flags=re.IGNORECASE)
        if heading_match:
            flush()
            section = heading_match.group(1).strip()
            continue

        paragraph.append(line)

    flush()
    return blocks


def _extract_pdf_blocks(path: Path) -> list[TextBlock]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise TextExtractionError("PDF extraction requires pypdf.") from exc

    try:
        reader = PdfReader(str(path))
        blocks: list[TextBlock] = []
        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for paragraph in re.split(r"\n\s*\n", text):
                normalized = re.sub(r"\s+", " ", paragraph).strip()
                if normalized:
                    blocks.append(TextBlock(text=normalized, page=page_index))
        return blocks
    except Exception as exc:
        raise TextExtractionError(f"Failed to extract PDF text from {path}.") from exc
