from types import SimpleNamespace

import pytest

import app.rag.chunking as chunking
from app.rag.chunking import chunk_document
from app.rag.models import Document


def make_document(content: str) -> Document:
    return Document(
        doc_id="d1",
        source="test.txt",
        content=content,
        metadata={},
    )


def test_chunk_document_with_overlap():
    doc = make_document("a" * 1000)
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert all(c.doc_id == "d1" for c in chunks)
    assert chunks[0].index == 0


def test_chunk_document_uses_custom_size():
    chunks = chunk_document(
        make_document("a" * 10),
        chunk_size=4,
        chunk_overlap=1,
    )

    assert [chunk.text for chunk in chunks] == ["aaaa", "aaaa", "aaaa"]
    assert [chunk.metadata["char_start"] for chunk in chunks] == [0, 3, 6]


def test_chunk_document_uses_default_settings(monkeypatch):
    monkeypatch.setattr(
        chunking,
        "get_settings",
        lambda: SimpleNamespace(chunk_size=5, chunk_overlap=2),
    )

    chunks = chunk_document(make_document("a" * 8))

    assert [chunk.text for chunk in chunks] == ["aaaaa", "aaaaa"]
    assert [chunk.metadata["char_start"] for chunk in chunks] == [0, 3]


def test_chunk_overlap_must_be_smaller_than_size():
    with pytest.raises(
        ValueError, match="chunk_overlap must be smaller than chunk_size"
    ):
        chunk_document(make_document("text"), chunk_size=4, chunk_overlap=4)


def test_chunk_size_must_be_positive():
    with pytest.raises(ValueError, match="chunk_size must be greater than 0"):
        chunk_document(make_document("text"), chunk_size=0, chunk_overlap=0)


def test_chunk_overlap_must_not_be_negative():
    with pytest.raises(ValueError, match="chunk_overlap must be >= 0"):
        chunk_document(make_document("text"), chunk_size=4, chunk_overlap=-1)


def test_empty_document_returns_empty_list():
    assert chunk_document(make_document(""), chunk_size=4, chunk_overlap=1) == []
