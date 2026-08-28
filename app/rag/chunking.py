"""Text chunking with overlap — Day 3."""

import uuid

from app.config import get_settings
from app.rag.models import Chunk, Document


def chunk_document(
    doc: Document,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    settings = get_settings()
    size = chunk_size if chunk_size is not None else settings.chunk_size
    overlap = (
        chunk_overlap if chunk_overlap is not None else settings.chunk_overlap
    )

    if size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0:
        raise ValueError("chunk_overlap must be >= 0")
    if overlap >= size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    text = doc.content
    if not text:
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + size, len(text))
        piece = text[start:end].strip()
        if piece:
            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    doc_id=doc.doc_id,
                    text=piece,
                    index=index,
                    metadata={
                        "source": doc.source,
                        "char_start": start,
                        "char_end": end,
                        **doc.metadata,
                    },
                )
            )
            index += 1
        if end >= len(text):
            break
        start = end - overlap

    return chunks
