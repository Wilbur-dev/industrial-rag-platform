"""Prompt builder with versioning — Week 2 Day 1."""

from dataclasses import dataclass
from enum import Enum


class PromptVersion(str, Enum):
    V1_GROUNDED = "v1_grounded"
    V2_STRICT_CITATIONS = "v2_strict_citations"
    V3_REFUSAL_AWARE = "v3_refusal_aware"


@dataclass(frozen=True)
class PromptTemplate:
    version: PromptVersion
    system: str
    user_template: str
    description: str


PROMPT_REGISTRY: dict[PromptVersion, PromptTemplate] = {
    PromptVersion.V1_GROUNDED: PromptTemplate(
        version=PromptVersion.V1_GROUNDED,
        description="Answer only from context; cite chunk numbers [1], [2].",
        system=(
            "Answer ONLY using the provided context. "
            "If the context is insufficient, say you don't know. "
            "Cite chunk numbers like [1], [2]."
        ),
        user_template="Context:\n{context}\n\nQuestion: {question}",
    ),
    PromptVersion.V2_STRICT_CITATIONS: PromptTemplate(
        version=PromptVersion.V2_STRICT_CITATIONS,
        description="Every factual sentence must end with a citation [n].",
        system=(
            "You are a grounded QA assistant. "
            "Use ONLY the numbered context blocks below. "
            "Every factual claim MUST end with a citation like [1] or [2]. "
            "If no block supports the answer, reply exactly: "
            '"I cannot answer from the provided context."'
        ),
        user_template=(
            "Context blocks:\n{context}\n\n"
            "Question: {question}\n\n"
            "Answer with mandatory inline citations:"
        ),
    ),
    PromptVersion.V3_REFUSAL_AWARE: PromptTemplate(
        version=PromptVersion.V3_REFUSAL_AWARE,
        description="Explicit refusal when context is weak or off-topic.",
        system=(
            "Answer using ONLY the context. "
            "If context is empty, irrelevant, or confidence would be low, "
            'respond: "I don\'t have enough information in the knowledge base." '
            "Never invent facts, dates, or names not in the context. "
            "Prefer short answers with [n] citations."
        ),
        user_template="Retrieved context:\n{context}\n\nUser question: {question}",
    ),
}


class PromptBuilder:
    """Build versioned prompts for grounded generation."""

    def __init__(self, version: PromptVersion | str | None = None) -> None:
        if version is None:
            self._version = PromptVersion.V1_GROUNDED
        elif isinstance(version, PromptVersion):
            self._version = version
        else:
            self._version = PromptVersion(version)

    @property
    def version(self) -> PromptVersion:
        return self._version

    @property
    def template(self) -> PromptTemplate:
        return PROMPT_REGISTRY[self._version]

    def build_messages(self, question: str, context: str) -> list[dict[str, str]]:
        tpl = self.template
        user_content = tpl.user_template.format(
            context=context,
            question=question,
        )
        return [
            {"role": "system", "content": tpl.system},
            {"role": "user", "content": user_content},
        ]

    @staticmethod
    def list_versions() -> list[dict[str, str]]:
        return [
            {
                "version": t.version.value,
                "description": t.description,
            }
            for t in PROMPT_REGISTRY.values()
        ]
