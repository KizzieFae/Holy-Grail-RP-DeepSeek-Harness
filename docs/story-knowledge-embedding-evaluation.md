# Story knowledge embedding evaluation (#50)

**Date:** 2026-08-27  
**Issue:** #50  
**Validation anchor:** `40bd4b7e5b0ba259ff400e252013ad5d76333dbd`

## Purpose

Gate production semantic-backend selection against agreed stress scenarios. This evaluation records **what was tested**, **what passed**, and **honest capability limits** — not marketing claims.

## Candidates evaluated

| Provider | ID | Dependencies | Offline | Windows / Py3.12 | Selected? |
|----------|-----|--------------|---------|-------------------|-----------|
| Deterministic hash | `deterministic_hash_v1` | none | yes | yes | Test control only |
| TF-IDF (in-process) | `tfidf_v1` | none | yes | yes | **Production default** |
| Sentence-transformers (`all-MiniLM-L6-v2`) | not pinned | heavy optional dep | partial | **Not selected** |

## Stress fixture — case-by-case results

| # | Scenario | TF-IDF result | Test / evidence |
|---|----------|---------------|-----------------|
| 1 | Rich occurrence retrieved through multiple semantic aspects | **Pass** — same `event_id` returned for distinct query phrasings | `StoryKnowledgeRetrievalTests.test_same_occurrence_multiple_semantic_aspects` |
| 2 | Repeated similar lies remain distinct and retrievable | **Pass** — three `event_id`s all returned | `test_repeated_lies_remain_distinct` |
| 3 | Later evidence relevant to one prior lie | **Pass (ranked path)** — budget forces `semantic_ranked`; relevant bench surfaces | `test_semantic_ranked_path` |
| 4 | Object/photograph recall through different wording | **Pass** — bronze key / garden gate / dusk queries hit `evt-rich` | `test_same_occurrence_multiple_semantic_aspects` |
| 5 | Irrelevant same-character occurrence ranks below relevant | **Partial** — TF-IDF separates better than hash on controlled collision fixture; not a guarantee for all paraphrase | `EmbeddingEvaluationTests.test_tfidf_beats_hash_on_lexical_collision` |
| 6 | Lexical/vocabulary collision — semantically wrong record should lose | **Pass on fixture** — TF-IDF score(relevant) > score(irrelevant) | same |
| 7 | Indirect contradiction / evidence relationship | **Deferred to Librarian** — retrieval supplies both records with provenance; applicability not decided by index | `AuthoredStoryPrecedenceTests.test_authored_and_story_both_retrievable_with_provenance` + architecture doc |

## Comparative notes

### Deterministic hash (`deterministic_hash_v1`)

- **Strengths:** perfectly reproducible; ideal unit-test control.
- **Weaknesses:** token-hash collisions; weak discrimination on paraphrase and collision cases.
- **Verdict:** test control only — not production ranking.

### TF-IDF (`tfidf_v1`)

- **Strengths:** zero new dependencies; fast; rebuildable; adequate on agreed fixture for candidate narrowing within eligible set E.
- **Weaknesses:** lexical — does not understand entailment, negation, or deep paraphrase; can fail on synonyms and cross-language wording.
- **Verdict:** simplest adequate baseline for #50 launch.

### Sentence-transformers (not pinned)

- **Strengths:** better semantic similarity on paraphrase (literature / prior art).
- **Weaknesses:** adds dependency and model artifact management; conflicts with current `pyproject.toml` zero-dependency baseline; Windows/offline pinning overhead.
- **Verdict:** deferred — may be re-evaluated against this fixture or an evolved successor.

## Selection

**Production default:** `TfidfEmbeddingProvider` in `v2/domain_api/story_semantic_index.py` (`EMBEDDING_PROVIDER_VERSION = "tfidf_v1"`).

**Test control:** `DeterministicHashEmbeddingProvider` via `SemanticIndexBackend(..., test_mode=True)`.

## Replacement boundary

Substituting a stronger `EmbeddingProvider` requires:

1. Re-run stress fixture (or evolved version) and update this document.
2. Rebuild indexes (`rebuild_semantic_index`) — persistence authority unchanged.
3. No change to Continuity truth, authored canon, or Librarian truth boundaries.

## Automated evidence command

```bash
python -m pytest v2/domain/tests/test_story_knowledge_issue_50.py::EmbeddingEvaluationTests -q
```
