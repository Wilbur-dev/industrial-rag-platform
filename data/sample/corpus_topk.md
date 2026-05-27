# Corpus TopK — Extended Retrieval Experiment Document

This document exists for **Week 2 Day 3–4** (`top_k` / `score_threshold` / Hit@K eval).
Ingest **only** into Qdrant collection `documents_topk` (`QDRANT_TOPK_EVAL_COLLECTION`), not the
same collection as `rag_overview.md` (`documents`), to avoid cross-document retrieval noise.

## Score threshold tuning in production

Operators often sweep `score_threshold` after deploying a new embedding model.
A threshold that is too high removes borderline-but-useful chunks and increases refusal rates in grounded QA.
A threshold that is too low lets noisy chunks through, which hurts citation validation and confuses the LLM.

Teams should log both `hits` (raw Qdrant results) and `hits_after_threshold` on every query.
Compare refusal rate and `grounding.reason=no_retrieval` when tightening thresholds.

## Top-k selection guidelines

`top_k` controls how many candidates enter the prompt budget.
Small k reduces latency and cost but risks missing the single chunk that contains the answer.
Large k improves recall for ambiguous questions but adds duplicate themes and dilutes attention.

For documentation corpora under five thousand tokens per page, k between 3 and 8 is a common starting band.
For multi-tenant SaaS knowledge bases, k is often paired with metadata filters (not shown in Week 2 baseline).

## Embedding drift monitoring

When upstream PDF parsers change, chunk boundaries shift even if `chunk_size` stays constant.
Drift dashboards track: average cosine score on a golden query set, MRR@10, and empty-retrieval percentage.
Alert when the weekly median top score drops more than five points without a config change.

## Latency versus quality trade-offs

Batch embedding during ingest amortizes cost; query-time embedding stays on the critical path.
Caching query vectors for repeated FAQs saves tens of milliseconds per request in internal benchmarks.
Rerankers (Week 3 placeholder in this repo) sit between vector retrieval and prompt assembly in many industrial stacks.

## Failure modes observed in staging

1. **Stale index** — Document updated on disk but never re-ingested; answers cite old policy numbers.
2. **Mixed collections** — Experimental ingest appended instead of replaced; top-k pulls unrelated sources.
3. **Threshold cliff** — A score of 0.29 filters everything when threshold is 0.30 despite semantically relevant text.
4. **Oversized k** — Model cites chunk [7] that was only included for breadth, not relevance.

## Runbook: reproducing a retrieval matrix

1. Ingest this file once into Qdrant (see `scripts/run_retrieval_experiments.py`).
2. Fix a canonical query such as “How should teams log hits_after_threshold?”
3. Sweep `top_k` ∈ {1, 3, 5, 10} and `score_threshold` ∈ {none, 0.3}.
4. Record `hit_count`, `top_score`, and `latency_ms` per cell.

## Glossary (retrieval)

| Term | Meaning |
|------|---------|
| Hit | A chunk returned by vector search before thresholding |
| Grounded | Answer supported by retrieved text and valid citation indices |
| Refusal | Model or template declines to answer for lack of evidence |

## Appendix A — Synthetic expansion section one

Platform SREs run game days that delete random Qdrant pods to validate client retry logic.
Clients should use exponential backoff and surface `error_code=retrieval_failed` to callers instead of raw stack traces.
During game day, increase `top_k` temporarily to compensate for partial index unavailability — only as a tactical knob.

## Appendix B — Synthetic expansion section two

Legal teams require audit logs listing chunk_id, score, and source path for every production answer.
The API response `citations` array is the user-visible slice of that audit trail.
Retention policies often keep citation metadata longer than raw chunk text in object storage.

## Appendix C — Synthetic expansion section three

Multilingual corpora need language tags in chunk metadata before tuning thresholds globally.
A threshold calibrated on English FAQs may be far too strict for shorter Japanese questions with different embedding geometry.
Evaluate per-locale slices instead of one global `score_threshold`.

## Appendix D — Synthetic expansion section four

Hybrid search (BM25 + vectors) is out of scope for Week 2 but frequently appears in interview follow-ups.
When explaining roadmap, mention inverted indexes for SKU codes and serial numbers that embeddings miss.
Keep the Week 2 story focused on cosine retrieval and post-filter thresholds to stay coherent.

## Appendix E — Closing checklist

- [ ] Confirm collection `points_count` matches expected chunk total after ingest
- [ ] Run experiments script twice; second run should skip duplicate ingest
- [ ] Capture terminal table screenshot for `week2-day3-experiment-matrix.png`
- [ ] Note any cell where `hit_count` drops to zero after thresholding
