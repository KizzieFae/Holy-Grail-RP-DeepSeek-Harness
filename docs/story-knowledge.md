# Story knowledge architecture (#50)

**Status:** Validated (anchor `40bd4b7e5b0ba259ff400e252013ad5d76333dbd`)  
**Issue:** [#50](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/50)  
**Related:** [#49](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/49) (Narrator authority — paused; not part of #50)

This document describes the **implemented** story-knowledge substrate: durable searchable evidence projected from authoritative story occurrences, integrated with Retrieval and Librarian mediation.

---

## 1. Authority domains (do not conflate)

| Domain | Role | Authoritative for | Mutated by story execution? |
|--------|------|-------------------|------------------------------|
| **Authored canon** | Character cards, scenario/template data, compiled authored knowledge | Authored baseline facts at session setup | **No** |
| **Continuity / committed story truth** | `PublicEvent`, `CanonAnchor`, session continuity state | What occurred and who knows it **now** | Yes (commit path only) |
| **Searchable story-knowledge corpus** | JSONL records per `memory_scope_id` | Durable **evidence** for retrieval | Append-only projection; not truth |
| **Semantic/search index** | `semantic_index_v1.json` | Candidate discovery within eligible set | Derived; rebuildable |
| **Librarian** | `KnowledgeAccessRequest` → bundle | Semantic applicability/adjudication | No truth writes |

**Story execution does not mutate authored canon.** When authoritative story progression legitimately supersedes an authored baseline for **current-state** questions, the authored source remains unchanged; mediation applies applicability, not a write-back.

---

## 2. Authored baseline vs story precedence

Accepted rule:

> **Authored canon is the baseline where no applicable authoritative story knowledge supersedes it. Applicable authoritative story knowledge governs current story state where legitimate story progression supersedes the authored baseline.**

**Not implemented (rejected):**

- newest-record-wins
- any-story-text-beats-canon
- routine second Librarian/canon plausibility inference pass

**Occurrence truth ≠ proposition truth.**  
Example: *"Kizzie told Ayame that Rin lives in Osaka"* authoritatively establishes the statement occurred; it does **not** automatically establish that Rin lives in Osaka. By contrast, authoritative progression *"Rin moved to Osaka"* may supersede authored baseline *"Rin lives in Kyoto"* for **current-state** queries.

**Historical queries** may correctly recover earlier/canonical state. Irreconcilable contradiction between genuinely authoritative story truth and canon is an **upstream integrity defect**, not re-proven on every retrieval.

---

## 3. Persistence layout

**Root:** `data/sessions/_story_knowledge/{memory_scope_id}/`

| File | Authoritative? | Purpose |
|------|----------------|---------|
| `records.jsonl` | **Corpus evidence** (not Continuity truth) | Append-oriented durable story records |
| `manifest.json` | No | Record index offsets, schema version, index metadata |
| `semantic_index_v1.json` | No | Derived TF-IDF vectors for ranking |

### Record identity

| `record_kind` | Primary identity | When used |
|---------------|------------------|-----------|
| `occurrence` | `event_id` | One committed eligible `PublicEvent` → one record |
| `derived` | `story_record_id` | Independently addressable enriched/concluded knowledge |

### Recovery behavior

- **Idempotent projection:** duplicate `event_id` / `story_record_id` append is a no-op.
- **Restart:** reload from JSONL + manifest.
- **Truncated tail:** `StoryKnowledgeRepository.recover_truncated_tail()` rebuilds manifest and truncates corrupt tail bytes.
- **Index rebuild:** `StoryKnowledgeService.rebuild_semantic_index()` reconstructs search state from JSONL alone.
- **Lazy backfill:** `project_after_commit` / `backfill_scope` project any missing `public_events` idempotently.

**Index failure** is auditable and surfaces as Librarian `retrieval_failure` when semantic narrowing is required — never as semantic `no_match`.

---

## 4. Post-commit projection lifecycle

```text
authoritative commit
  → session persist (Continuity authoritative)
  → knowledge_service.promote_after_commit
      → scope learned-world promotion (unchanged #50)
      → story_knowledge_service.project_after_commit
          → project_missing_occurrences (PublicEvent → StoryKnowledgeRecord)
          → JSONL append (idempotent)
          → best-effort semantic index upsert
```

Authoritative commit **does not depend** on index success.

**Occurrence evidence (#51):** When `PublicEvent.occurrence_evidence` is present, `story_knowledge_projection` composes `StoryEvidence.committed_text` from the audibility-safe `summary`, globally embeddable `contributions`, and permitted `triggering_user` excerpt. Scoped private evidence is **not** included in globally searchable embedding material. Thin legacy events without `occurrence_evidence` continue to project `summary` only.

**Implementation:** `v2/domain_api/knowledge_service.py`, `story_knowledge_projection.py`, `story_knowledge_service.py`, wired from `session_repository.py`.

---

## 5. Retrieval pipeline

```text
InformationNeed (Librarian)
  → RetrievalAccessRequest(s) per information class
  → authored + compiled + scope + story providers
  → hard scope / class / visibility eligibility
  → live epistemic eligibility (occurrences via event_id)
  → referent constraints
  → eligible set E
  → measure serialized evidence S(E) vs budget B
  → full_eligible | semantic_ranked (story provider)
  → merge candidates (provenance preserved)
  → one Librarian semantic mediation
  → mediation_outcome + LibrarianKnowledgeBundle
```

**Information classes (story):** `story_occurrence`, `story_derived` (`retrieval_contract.py`).

**Vector/search rank** narrows candidates within **already-eligible** set E; it does **not** determine truth authority or precedence.

**Both provenance domains** (authored vs story) may appear in the same mediation catalog; provenance fields distinguish them (`provenance_domain`, `knowledge_lane`, `source_kind`).

**Implementation:** `retrieval_service.py`, `story_knowledge_retrieval.py`, `librarian_service.py`, `librarian_mapper.py`.

---

## 6. Epistemics

| Concern | Authority | Storage |
|---------|-----------|---------|
| **Current occurrence visibility** | Live `PublicEvent.known_by` / `knowledge_level_for` | Continuity session state |
| **Historical establishment** | Provenance only | Optional `establishment_epistemic.known_by_at_commit` on record |
| **Derived visibility** | `EpistemicAuthorityRef` from establishment decision | On derived record |

- Story records **do not** carry a competing mutable `known_by`.
- Later knowledge propagation (`share_event_knowledge`, etc.) becomes visible at query time **without** rewriting JSONL occurrence records.
- Forbidden viewers are excluded **before** semantic ranking.

**Resolver:** `story_knowledge_epistemic.py`

**`inherit_source_events`:** does **not** universally mean “viewer knows all sources ⇒ knows derived proposition.” Valid only where inheritance is part of the authoritative establishment decision.

---

## 7. Derived knowledge and agent authority

#50 provides a **neutral persistence/retrieval substrate**:

- `DerivedStoryRecordSubmission` + `StoryKnowledgeService.submit_derived_record()`
- Records **already-authorized** establishment via `EpistemicAuthorityRef`

#50 does **not** grant Narrator, Director, Character, Storyteller, Librarian, or any other agent authority to **establish new story truth**. Agent-specific establishment remains governed separately (**#49** for Narrator).

---

## 8. Semantic backend (current selection)

| Aspect | Choice |
|--------|--------|
| **Production default** | `TfidfEmbeddingProvider` (`tfidf_v1`) in `story_semantic_index.py` |
| **Test control** | `DeterministicHashEmbeddingProvider` (`test_mode=True`) |
| **Protocol** | `SemanticIndexBackend` — replaceable derived infrastructure |

TF-IDF provides **lightweight lexical-semantic ranking** within eligible candidates. It is **not** deep neural semantic understanding. Stronger embedding backends may be substituted later **without** changing persistence or truth authority.

Evaluation evidence: [story-knowledge-embedding-evaluation.md](./story-knowledge-embedding-evaluation.md)

---

## 9. Mediation outcomes

`LibrarianKnowledgeBundle.mediation_outcome` (`story_knowledge_contract.MediationOutcome`):

| Outcome | Meaning |
|---------|---------|
| `match` | Usable mediated entries returned |
| `no_match` | Eligible material did not satisfy the information need |
| `ambiguous` | Competing applicable interpretations |
| `forbidden` | Request or content blocked by policy/visibility |
| `retrieval_failure` | Required retrieval/index path failed (e.g. missing semantic index when `semantic_ranked` required) |
| `mediation_failure` | Contextual mediation rejected/unavailable |

**Critical:** `retrieval_failure`, `mediation_failure`, `forbidden`, and `ambiguous` are **not** `no_match`.

---

## 10. Scope isolation

`memory_scope_id` is the intentional **story-continuity universe**. Sessions with the same authored cards but different scopes do not share story JSONL. Cross-session aggregation beyond scope remains **out of scope** for #50.

---

## 11. Module map

| Module | Role |
|--------|------|
| `story_knowledge_contract.py` | Schemas, `MediationOutcome`, `EpistemicAuthorityRef` |
| `story_knowledge_repository.py` | JSONL + manifest persistence |
| `story_knowledge_projection.py` | `PublicEvent` → occurrence record |
| `story_knowledge_epistemic.py` | Live eligibility resolver |
| `story_knowledge_retrieval.py` | Evidence-budget selection |
| `story_knowledge_service.py` | Orchestration, backfill, derived submit |
| `story_semantic_index.py` | TF-IDF index backend |

**Tests:** `v2/domain/tests/test_story_knowledge_issue_50.py`  
**Forensic record:** `governance/records/issue-50-story-knowledge-forensic-record.md`
