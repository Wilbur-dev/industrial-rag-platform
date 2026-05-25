from app.rag.chunking import chunk_document
from app.rag.models import Document


def test_chunk_document_with_overlap():
    doc = Document(
        doc_id="d1",
        source="test.txt",
        content="a" * 1000,
        metadata={},
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert all(c.doc_id == "d1" for c in chunks)
    assert chunks[0].index == 0
