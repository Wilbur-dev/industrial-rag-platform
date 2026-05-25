# Industrial RAG Platform — Week 1 Sample Document

## What is RAG?

Retrieval-Augmented Generation (RAG) combines **document retrieval** with **language model generation**.
Instead of relying only on the model's training data, the system fetches relevant chunks from your knowledge base first.

## Core Pipeline (Week 1)

1. **Ingestion** — Parse PDF and Markdown files with metadata.
2. **Chunking** — Split text with configurable `chunk_size` and `chunk_overlap`.
3. **Embedding** — Encode chunks using a sentence-transformer model (`torch.no_grad`, batch inference).
4. **Vector DB** — Store vectors in Qdrant; search uses **cosine similarity**.
5. **Query** — Embed the question, retrieve top-k chunks, generate a **grounded** answer with citations.

## Why chunk overlap?

Overlap preserves context across chunk boundaries. Without overlap, a sentence split across two chunks might lose meaning in retrieval.

## Hallucination control

Grounded generation means the answer must cite retrieved context. If retrieval returns nothing useful, the system should say it does not know rather than invent facts.

## Interview talking points

- **Why centralized config?** — Same parameters in dev/staging/prod; no magic numbers in code.
- **Why structured logging?** — Machine-parseable logs for latency, errors, and retrieval quality in production.
- **Why Qdrant?** — Purpose-built vector DB with filtering, persistence, and horizontal scaling path.
