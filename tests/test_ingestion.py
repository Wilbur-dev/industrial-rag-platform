from app.rag.ingestion import ingest_upload


def test_ingest_markdown():
    text = b"# Hello\n\nRAG platform week 1."
    doc = ingest_upload("readme.md", text)
    assert doc.metadata["format"] == "markdown"
    assert "RAG" in doc.content
