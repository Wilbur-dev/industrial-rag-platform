"""PDF / Markdown ingestion — Day 2."""

import uuid
from io import BytesIO
from pathlib import Path

from markdown_it import MarkdownIt
from pypdf import PdfReader

from app.rag.models import Document


def _read_pdf_bytes(data: bytes, source: str) -> Document:
    reader = PdfReader(BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages.append(text)
    content = "\n\n".join(pages).strip()
    return Document(
        doc_id=str(uuid.uuid4()),
        source=source,
        content=content,
        metadata={"format": "pdf", "page_count": len(reader.pages)},
    )


def _read_markdown_text(text: str, source: str) -> Document:
    md = MarkdownIt()
    # Keep raw markdown for chunking; render optional for display
    html_preview = md.render(text[:500]) if text else ""
    return Document(
        doc_id=str(uuid.uuid4()),
        source=source,
        content=text.strip(),
        metadata={"format": "markdown", "html_preview_len": len(html_preview)},
    )


def ingest_file(path: Path) -> Document:
    suffix = path.suffix.lower()
    source = str(path.name)
    if suffix == ".pdf":
        return _read_pdf_bytes(path.read_bytes(), source)
    if suffix in {".md", ".markdown"}:
        return _read_markdown_text(path.read_text(encoding="utf-8"), source)
    raise ValueError(f"Unsupported file type: {suffix}")


def ingest_upload(filename: str, data: bytes) -> Document:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _read_pdf_bytes(data, filename)
    if lower.endswith(".md") or lower.endswith(".markdown"):
        return _read_markdown_text(data.decode("utf-8"), filename)
    raise ValueError(f"Unsupported upload: {filename}")
