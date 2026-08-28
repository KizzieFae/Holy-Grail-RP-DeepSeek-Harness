# Issue #51 — Occurrence evidence forensic record

**Issue:** [#51](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51)  
**Implementation anchor:** _(recorded at commit)_  
**Consensus:** [Full-weight consensus comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5449968967)

## Problem (before)

Promotion policy gave `state_changes[0]` (generic classifier templates) strict precedence over move-specific committed meaning. #50 projected only thin `summary` → `committed_text`.

## Solution chain

```text
producer inputs (move, director_decision, user history)
  → classify_turn_consequences (metadata retained in state_changes)
  → build_move_specific_summary (specific meaning first; templates fallback)
  → build_occurrence_evidence_for_promotion (bounded companion)
  → public_safe_event_summary (audibility gate on summary)
  → PublicEvent persisted (+ optional occurrence_evidence)
  → epistemic routing (known_by authoritative)
  → story_knowledge_projection composes committed_text from summary + global evidence
  → authorized retrieval meaning
```

## `PublicEvent.occurrence_evidence` structure

| Subfield | Purpose |
|----------|---------|
| `contributions[]` | `{producer, contribution_kind, content, metadata?}` — generic across event classes |
| `triggering_user?` | `{entry_id, speaker, content?, hg_round_id?, sequence_index?}` |
| `structured_fact_refs[]` | `{ref_kind, ref_id}` — grounding markers, resolved outcomes |
| `scoped_evidence[]?` | Non-public speech; excluded from global embedding |

## Bounded limits (implementation)

| Limit | Value | Rationale |
|-------|-------|-----------|
| Contribution content | 500 chars | Semantically sufficient without transcript dump |
| Contributions per event | 5 | Character + Director + spare |
| Trigger excerpt | 300 chars | Causal context without full user history |
| Scoped evidence entries | 3 | Rare multi-private beats |
| Fact refs | 12 | Markers + resolved outcomes |
| Composed committed_text | 1000 chars | Retrieval-useful cap (2× summary) |

## Representative before/after

| Case | Before `summary` | After `summary` + evidence |
|------|------------------|----------------------------|
| Gun on table + PHYSICAL_STATE_SET | Generic physical template | `Alice placed the gun on the table` + action contribution + marker ref |
| Revelation dialogue | `revealed significant information` | Dialogue proposition in summary/contributions |
| Refusal | Generic refusal template | Specific refusal line preserved |
| Character + Director env | Director text dropped | Both in `contributions[]` |
| User trigger | None | `triggering_user.entry_id` + bounded excerpt |

## #50 adapter boundary

- **Changed:** `project_occurrence_from_public_event` composes `committed_text` via `globally_embeddable_occurrence_text`.
- **Unchanged:** occurrence-first identity, `event_id`, live `known_by`, derived records, Librarian mediation, truth authority.

## Compatibility

- `occurrence_evidence` optional; `PublicEvent.from_dict` defaults preserve old sessions.
- No mandatory continuity JSON migration.
- Historical thin JSONL records remain valid; richer projection on re-project when events gain evidence.

## Validation

- `v2/domain/tests/test_issue_51_occurrence_evidence.py` (promotion, multi-producer, trigger, epistemic, #50 integration, backward compat)
- Regression: `v2/domain/tests/test_story_knowledge_issue_50.py`

## Rejected implementation alternatives

- Event-type-specific schema fields (`refusal_object`, etc.)
- Renaming `state_changes`
- Separate Issue for #50 adapter
- Copying full `structured_move` or Continuity registries onto `PublicEvent`
