from app.rag.prompts import PromptBuilder, PromptVersion


def test_prompt_versions_listed():
    versions = PromptBuilder.list_versions()
    assert len(versions) >= 3
    ids = {v["version"] for v in versions}
    assert PromptVersion.V2_STRICT_CITATIONS.value in ids


def test_build_messages_includes_context():
    builder = PromptBuilder(PromptVersion.V3_REFUSAL_AWARE)
    messages = builder.build_messages("What is RAG?", "[1] RAG is retrieval augmented.")
    assert messages[0]["role"] == "system"
    assert "RAG is retrieval" in messages[1]["content"]
    assert "What is RAG?" in messages[1]["content"]
