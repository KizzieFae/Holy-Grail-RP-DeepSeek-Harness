# Issue #50 — Story Knowledge Forensic / Execution Record

**Status:** Validated (see §12 for validation anchor)  
**Issue:** [#50 — Story knowledge storage, retrieval, and Librarian mediation](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50)  
**Type:** `design_gap`  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full  
**Planning anchor:** `4843d1b8ea9e8019823a10f684f0e4b8ee9f521b`  
**Implementation / validation anchor:** *(set at commit — see §12)*  
**#49 boundary:** Not modified; remains paused at `investigating`

**Maintainer architecture doc:** [docs/story-knowledge.md](../../docs/story-knowledge.md)  
**Embedding evaluation:** [docs/story-knowledge-embedding-evaluation.md](../../docs/story-knowledge-embedding-evaluation.md)

---

## 0. Record purpose

This record preserves the **full decision lineage** for #50 so auditors can reconstruct:

```text
request → evidence/investigation → proposed decision → Governance challenge/refinement
  → accepted decision → implementation → validation evidence
```

without depending on chat transcripts. Issue comments provide durable permalinks; this file provides structured inventory, rejected alternatives, implementation anchors, and test evidence.

---

## 1. Source decision lineage (Issue permalinks)

| Stage | Permalink | Summary |
|-------|-----------|---------|
| Intake → investigating | [#issuecomment-5448258396](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448258396) | Full bootstrap activation; execution anchor `4843d1b`; #49 separated |
| Investigation evidence | [#issuecomment-5448259429](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448259429) | Repository architecture survey; gaps; alternatives |
| Governance refinement | [#issuecomment-5448501216](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448501216) | Ten challenges; evidence-budget; occurrence-first; epistemics |
| Investigating → consensus_reached | [#issuecomment-5448673305](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448673305) | Accepted architecture summary; explicit non-changes |
| Implementation planning | [#issuecomment-5448847909](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448847909) | Component mapping; test matrix; sequencing |
| Precedence refinement | [#issuecomment-5448940780](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5448940780) | Authored baseline / story supersession rule |
| Implementation authorization | Governance chat authorization (2026-08-27) | GRANTED for #50 only; effective weight full |
| Consensus → implemented | [#issuecomment-5449017935](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50#issuecomment-5449017935) | Landed implementation summary; tests |
| Implemented → validated | *(this cycle — §12)* | Formal validation transition |

**Issue body:** consensus architecture section + `Current status:` field (updated each transition).

---

## 2. Decision inventory

### A. Why #50 exists

| Decision | Evidence |
|----------|----------|
| Generalized story-knowledge storage/retrieval separated from Narrator-specific **#49** | Intake comment; investigation §1 gaps |
| #50 is prerequisite substrate; **#49** paused | Consensus transition; implementation authorization boundary |
| #49 must not be modified during #50 | All transition comments; git scope review |

### B. Two-layer knowledge records

| Decision | Rationale | Implementation |
|----------|-----------|----------------|
| Structural/contextual grounding **and** rich semantic evidence | IDs alone insufficient; prose alone ambiguous | `StoryKnowledgeRecord.stable_refs`, `grounding_markers`, `StoryEvidence` (`story_knowledge_contract.py`) |
| Stable occurrence identity + meaningful evidence | Librarian reads full bounded evidence | `event_id` + `evidence.committed_text` + optional context window (`story_knowledge_projection.py`) |

### C. Occurrence-first model

| Accepted | Rejected |
|----------|----------|
| One committed `PublicEvent` → one rich searchable occurrence (`event_id`) | Mandatory write-time semantic atomization |
| Derived `story_record_id` only when separate identity required | Universal multi-record split per event |

**Implementation:** `project_occurrence_from_public_event()`, `record_kind="occurrence"`.

### D. Inclusion policy

| Accepted | Rejected |
|----------|----------|
| Meaningful committed events enter via existing `should_create_event` / promotion policy | Semantic “importance” classifier as write gate |
| Technical/audit/presentation artifacts excluded (not story knowledge) | Indexing full transcript as lore |

**Implementation:** projection from `fixture.manager.public_events` only.

### E. Retrieval selection (evidence budget)

**Rejected:** fixed 50–75 record crossover threshold.

**Accepted:**

```text
hard eligibility → eligible set E → S(E) vs budget B → full_eligible | semantic_ranked
```

| Rationale | Fixed counts ignore variable evidence size and existing char budgets |
|-----------|----------------------------------------------------------------------|

**Implementation:** `select_story_candidates()` in `story_knowledge_retrieval.py`; diagnostics `story_selection_path`, `story_eligible_count`, `story_eligible_chars` in `retrieval_contract.py`.

### F. Semantic/vector retrieval

| Decision | Implementation |
|----------|----------------|
| Index is retrieval infrastructure, not truth | `semantic_index_v1.json` documented as derived |
| Search narrows within E; Librarian adjudicates applicability | `RetrievalService` + `LibrarianService` unchanged separation |
| No dedicated vector DB required | `SemanticIndexBackend` in-process |
| TF-IDF selected after evaluation | `TfidfEmbeddingProvider` (`tfidf_v1`) |
| Deterministic hash = test control | `DeterministicHashEmbeddingProvider`, `test_mode=True` |
| Stronger embeddings replaceable | `EmbeddingProvider` protocol |

### G. Epistemic authority

| Accepted | Rejected |
|----------|----------|
| Live `PublicEvent.known_by` at query via `event_id` | Stale persisted `known_by` as current authority |
| `establishment_epistemic` provenance-only on records | Second mutable `known_by` on JSONL records |
| Forbidden excluded before ranking | Leakage through embeddings to ineligible viewers |

**Implementation:** `story_knowledge_epistemic.py` — `_event_knowable()`, `story_record_epistemically_eligible()`.

### H. Derived-record epistemics

| Evolution | Result |
|-----------|--------|
| Initial generic visibility-from-sources idea | Governance objection |
| **Accepted:** #50 records/references authoritative epistemic decision | `EpistemicAuthorityRef` |
| Source-event knowledge ≠ derived proposition knowledge unless explicit | `inherit_source_events` modes; test `test_inherit_source_events_does_not_auto_imply_knowledge` |

**Implementation:** `DerivedStoryRecordSubmission`, `submit_derived_record()`.

### I. Authored canon vs story knowledge

**Accepted rule:**

> Authored canon is baseline. Applicable authoritative story knowledge governs current story state when legitimate progression supersedes the baseline.

| Also recorded | |
|---------------|---|
| Story never writes back into authored canon | Projection only; snapshot unchanged (test `test_authored_snapshot_unchanged_after_projection`) |
| Not newest-wins / not any-story-beats-canon | Documented in `docs/story-knowledge.md` |
| Claims/beliefs ≠ facts | Occurrence establishes event, not embedded proposition |
| No routine second plausibility pass | Single Librarian mediation; no canon-validation LLM in retrieval |
| Irreconcilable contradiction = upstream integrity defect | Documented |

### J. Librarian role

| Decision | Implementation |
|----------|----------------|
| Authored + story candidates in one mediation | `RetrievalService` merge; provenance on candidates |
| One normal semantic mediation | Existing `LibrarianService.access_knowledge` path |
| Librarian not truth authority | Unchanged Continuity write boundary |
| Search rank ≠ truth precedence | `backend_retrieval_rank` weak prior only |

**Mediation outcomes:** `mediation_outcome` on `LibrarianKnowledgeBundle`; `_compute_mediation_outcome()` in `librarian_service.py`.

### K. Story-scope isolation

| Decision | Implementation |
|----------|----------------|
| `memory_scope_id` = story universe | Per-scope directory under `_story_knowledge/` |
| Same cards, different scopes → no leak | `test_scope_isolation` |
| Cross-session aggregation | **Deferred** (out of #50 scope) |

### L. Persistence choice

| Rejected | Accepted |
|----------|----------|
| Monolithic JSON per scope | Append-oriented JSONL + manifest |
| Manifest/index as truth | Rebuildable non-authoritative metadata |
| Index failure → no_match | `retrieval_failure` / `story_semantic_index_failed` |

**Implementation:** `StoryKnowledgeRepository`; `recover_truncated_tail()`, `rebuild_semantic_index()`.

### M. Agent-authority boundary

| Decision | Notes |
|----------|-------|
| #50 = storage/retrieval substrate only | No runtime agent establishment authority |
| #49 will census agents / Narrator authority | Paused; not implemented |
| Child issue possible if census exposes broader gap | Governance option; not created in #50 |

---

## 3. Rejected and deferred alternatives

### Rejected

| Alternative | Why rejected |
|-------------|--------------|
| Fixed 50–75 record crossover | Ignores variable evidence size; char budgets already exist |
| Mandatory write-time semantic atomization | Cost, duplication, fragmentation; occurrence-first sufficient |
| Semantic importance classifier | Deterministic promotion policy already gates inclusion |
| Stale persisted `known_by` on records | Live Continuity is authoritative; propagation without rewrite |
| Full-story model-context scanning | Transcript remains separate; searchable corpus is projected evidence |
| Dedicated vector DB (initial requirement) | No repo evidence; in-process backend adequate |
| Mandatory LLM summary at write time | `evidence.summary` optional from existing summary only |
| Generic derived visibility inventing epistemic authority | `EpistemicAuthorityRef` records decisions; does not invent |
| Newest-record-wins | Violates authored baseline + applicability model |
| Canon-always-wins | Ignores legitimate story progression |
| Story-text-always-wins | Claims/lies ≠ facts |
| Routine second Librarian/canon-validation inference | Legality at commit; one mediation pass |
| Story writes back into authored canon | Authored sources immutable at runtime |

### Deferred (not rejected)

| Item | Status |
|------|--------|
| JSONL compaction policy | Minimal append-only sufficient |
| `episodic_session` behind Retrieval façade | Contract exists; not wired in #50 |
| Cross-scope aggregation beyond `memory_scope_id` | Out of #50 scope |
| Sentence-transformer production backend | Evaluated; not selected; replaceable later |
| Neo4j / graph store | Not authorized |
| #49 Narrator establishment authority | Separate governed cycle |

---

## 4. Implementation traceability

| Accepted decision | File / symbol | Notes |
|-------------------|---------------|-------|
| Occurrence schema | `story_knowledge_contract.py` — `StoryKnowledgeRecord`, `StoryEvidence` | `STORY_KNOWLEDGE_SCHEMA_VERSION = 1` |
| Derived schema | `DerivedStoryRecordSubmission`, `EpistemicAuthorityRef` | Neutral submit API |
| JSONL persistence | `story_knowledge_repository.py` — `StoryKnowledgeRepository` | `records.jsonl`, `manifest.json` |
| Projection | `story_knowledge_projection.py` — `project_occurrence_from_public_event` | Post-commit hook |
| Post-commit seam | `knowledge_service.py` — `promote_after_commit` | After scope promotion |
| Repository wiring | `session_repository.py` — `_story_knowledge_repo` | `data/sessions/_story_knowledge/` |
| Live epistemics | `story_knowledge_epistemic.py` | `event_id` resolver |
| Evidence budget | `story_knowledge_retrieval.py` — `select_story_candidates` | `full_eligible` / `semantic_ranked` |
| Retrieval integration | `retrieval_service.py` | `story_occurrence`, `story_derived` classes |
| TF-IDF backend | `story_semantic_index.py` — `TfidfEmbeddingProvider` | `tfidf_v1` |
| Mediation outcomes | `librarian_contract.py`, `librarian_service.py` | Six outcomes |
| Librarian wiring | `kernel.py` — `_librarian_service` | story repo passed to Retrieval |
| Provenance fields | `story_knowledge_retrieval.py` — `record_to_candidate` | `provenance_domain: story` |
| Information classes | `retrieval_contract.py` | Extended `ALL_INFORMATION_CLASSES` |
| Mapper budgets | `librarian_mapper.py` | Story class recall caps |

---

## 5. Validation evidence (behavioral claims)

**Suite:** `v2/domain/tests/test_story_knowledge_issue_50.py`  
**Regression:** `test_retrieval_access_s0_s1.py`, `test_librarian_read_s2a.py`, `test_character_knowledge_s38.py`  
**Full domain:** `v2/domain/tests/` (540 tests at validation)

| Behavioral claim | Test method |
|------------------|-------------|
| Append/restart persistence | `test_append_restart_idempotent` |
| Idempotent duplicate projection | `test_append_restart_idempotent` |
| Truncated JSONL tail recovery | `test_truncated_tail_recovery` |
| Index rebuild from JSONL | `test_rebuild_index_from_jsonl_only` |
| Multi-aspect occurrence retrieval | `test_same_occurrence_multiple_semantic_aspects` |
| Repeated lies distinct | `test_repeated_lies_remain_distinct` |
| Semantic-ranked path under budget pressure | `test_semantic_ranked_path` |
| Live epistemic propagation without rewrite | `test_forbidden_then_propagated` |
| Forbidden filtering | `test_forbidden_then_propagated` (blocked phase) |
| Scope isolation | `test_scope_isolation` |
| Full-eligible path | `test_full_eligible_path` |
| Index failure ≠ no_match | `test_missing_index_is_retrieval_failure_not_no_match` |
| Authored + story coexist with provenance | `test_authored_and_story_both_retrievable_with_provenance` |
| Authored snapshot unchanged | `test_authored_snapshot_unchanged_after_projection` |
| Claim occurrence ≠ progression supersession | `test_claim_does_not_supersede_authored_fact` |
| Derived record fixture | `test_derived_record_persists_with_authority_ref` |
| No auto derived knowledge from sources | `test_inherit_source_events_does_not_auto_imply_knowledge` |
| Mediation retrieval_failure distinct | `test_librarian_mediation_outcome_retrieval_failure` |
| TF-IDF lexical stress | `test_tfidf_beats_hash_on_lexical_collision` |

### TF-IDF stress cases (case-by-case)

| Case | Result | Evidence |
|------|--------|----------|
| 1. Rich occurrence, multiple aspects | Pass | `test_same_occurrence_multiple_semantic_aspects` |
| 2. Repeated similar lies | Pass | `test_repeated_lies_remain_distinct` |
| 3. Later evidence vs prior lie (ranked path) | Pass | `test_semantic_ranked_path` |
| 4. Object recall, wording variants | Pass | `test_same_occurrence_multiple_semantic_aspects` (queries) |
| 5. Irrelevant same-character ranks lower | Partial — TF-IDF better than hash on collision fixture | `test_tfidf_beats_hash_on_lexical_collision` |
| 6. Lexical collision | Pass (TF-IDF > hash on fixture) | same |
| 7. Indirect contradiction | Deferred to Librarian; retrieval supplies both with provenance | Architecture doc; mixed retrieval test |

**Honest capability bound:** TF-IDF is a lightweight lexical baseline, not neural semantic understanding. Suitable for candidate narrowing within E; not a substitute for Librarian applicability reasoning.

---

## 6. Activation and execution timeline

| When | HEAD / anchor | Phase |
|------|---------------|-------|
| Investigation activation | `4843d1b` | `investigating` |
| Consensus recorded | `4843d1b` | `consensus_reached` |
| Implementation landed | *(implementation commit)* | `implemented` |
| Formal validation | *(validation commit — §12)* | `validated` |

---

## 7. Documentation deliverables

| File | Role |
|------|------|
| `docs/story-knowledge.md` | Maintainer architecture (authority, persistence, retrieval, epistemics) |
| `docs/story-knowledge-embedding-evaluation.md` | TF-IDF selection evidence |
| `docs/rp-data-layout.md` | On-disk layout under `_story_knowledge/` |
| `docs/architecture.md` | NI layer integration note |
| `PACKET_CONTRACTS.md` | Retrieval/bundle contract pointer |
| `MODULE_INDEX.md` | Symptom → module routing |
| `CANONICAL_KNOWLEDGE_MODEL.md` | Knowledge model snapshot |
| `governance/sources/architecture-overview.md` | Standing architecture table row |

---

## 8. Hygiene

- Removed `.tmp-issue-50-*` scratch artifacts before commit (not durable records).
- No generated runtime session/story data committed.
- **#49:** no file modifications.

---

## 9. Residual deferred work

- JSONL compaction (if corpus growth requires)
- `episodic_session` / `cross_scope_relationship` Retrieval wiring
- Sentence-transformer re-evaluation against evolved fixture
- Full live Librarian LLM precedence behavior (depends on DSH inference; #49 boundary)
- Cross-session story aggregation

---

## 10. Closure-readiness (for Governance)

| Criterion | Status |
|-----------|--------|
| Implementation complete | Yes |
| Stable commit anchor | Yes (§12) |
| Tests complete | Yes |
| Behavioral validation complete | Yes (see §5) |
| Documentation complete | Yes |
| Forensic record complete | Yes (this file) |
| Repository hygiene clean | Yes |
| Deferred work identified | Yes (§9) |
| #49 untouched | Yes |

**Closure authorization:** NONE — await Governance closure decision after `validated`.

---

## 11. §B.5 validation transition

*(Completed in this cycle — permalink and SHA recorded in Governance return and Issue comment.)*

---

## 12. Validation anchor

*(Populated after commit in this cycle.)*
