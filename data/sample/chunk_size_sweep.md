# Chunk Size Sweep — Single Canonical Document

This file is ingested **unchanged** into separate Qdrant collections (`*_cs128`, `*_cs256`, `*_cs512`)
so only `chunk_size` differs between runs. Used by `scripts/run_retrieval_experiments.py` Part B.

## Overlap policy

All sweeps in this experiment use **chunk_overlap=64** characters.
When `chunk_size` is 128, overlap is half of a chunk; when `chunk_size` is 512, overlap is smaller relative to chunk length.
Keep overlap fixed so observed differences attribute primarily to chunk length, not overlap ratio drift.

## Expected chunk counts (approximate)

For this markdown body (~3200 characters):

| chunk_size | Approx. chunks |
|------------|----------------|
| 128 | 28–32 |
| 256 | 14–16 |
| 512 | 7–8 |

## Retrieval behavior hypotheses

Smaller chunks raise the number of vectors in the index, which can improve precision for pinpoint facts
but increases the chance that top-k results are fragmented sentences.
Larger chunks preserve paragraph context, often boosting coherence for summary-style questions
while risking that a single chunk mixes unrelated sections.

## Canonical evaluation queries

Use the **same** questions for every collection:

1. *What overlap policy does the chunk size sweep document use?*
2. *How does smaller chunk_size affect precision versus fragmentation?*
3. *What approximate chunk counts are listed for chunk_size 256?*

## Monitoring ingest idempotency

Each collection should contain points whose payload `source` equals `chunk_size_sweep.md`.
Re-running the experiment script must skip ingest when that source already exists in the target collection.
The default application collection used for top-k and threshold experiments must remain separate.

## Section A — embedding batching

Domain-tuned encoders benefit from batch size 32 on GPU and batch size 8 on CPU-only laptops.
Normalize embeddings when the model card does not already L2-normalize outputs.
Log embedding latency per batch during large ingests to catch thermal throttling on long runs.

## Section B — Qdrant collection naming

Suffix collections with `_cs{size}` to avoid overwriting the production `documents` collection.
Never ingest this sweep file into the main collection during Part B; Part A uses `corpus_topk.md` instead.

## Section C — score threshold interaction

Thresholding after retrieval is independent of chunk_size but couples in user-visible quality:
tiny chunks with low scores may be entirely filtered out when threshold is 0.35, yielding empty context.
Document both raw hit counts and post-threshold counts when publishing experiment tables.

## Section D — interview narrative

Explain that fair chunk_size studies hold document text constant, vary only chunking parameters,
and isolate indexes per configuration so vectors from different splits never compete in one search.
