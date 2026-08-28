# Issue #51 — Occurrence evidence forensic record

**Issue:** [#51](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51)  
**Implementation anchor:** `6cec5938dc54273176dfa592a89e881d30d63236`  
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

**Validation anchor:** `9d9204148300afd2797fc243350ea012f1c2ec90`

**Scoped diff:** `356a0b28adc656ac52a96a3e8cb48481178cd048` → `9d92041` (13 files; product + tests + docs + forensic only)

**Determination:** PASS — Full-weight independent validation (2026-08-28)

| Area | Result |
|------|--------|
| PublicEvent contract (optional `occurrence_evidence`, backward compat) | PASS |
| Summary precedence (specific > template) | PASS |
| Character contribution fidelity | PASS |
| User-trigger provenance (entry_id, skip-aware, bounded) | PASS |
| Multi-producer (Character + Director) | PASS |
| Structured fact refs (grounding markers; resolved-outcome append path) | PASS |
| Epistemic (scoped/private excluded from global embedding) | PASS |
| #50 adapter (bounded `committed_text` composition only) | PASS |
| Historical compatibility / projection idempotency | PASS |
| Bounded limits (deterministic truncation) | PASS |
| Promotion coverage unchanged | PASS |
| Architecture conformance (10 questions) | PASS |

**Commands executed at validation:**

```text
python -m pytest v2/domain/tests/test_issue_51_occurrence_evidence.py -q                    → 11 passed
python -m pytest v2/domain/tests/test_story_knowledge_issue_50.py -q                        → 17 passed
python -m pytest v2/domain/tests/test_continuity_issue_140_v2.py -q                         → (in targeted)
python -m pytest v2/domain/tests/test_scene_grounding.py -q                                 → (in targeted)
python -m pytest v2/domain/tests/test_perception_audibility.py -q                           → (in targeted)
python -m pytest v2/domain/tests/test_continuity_mutation_pipeline.py -q                    → (in targeted)
python -m pytest v2/domain/tests/test_issue_51_occurrence_evidence.py \
  v2/domain/tests/test_story_knowledge_issue_50.py \
  v2/domain/tests/test_continuity_issue_140_v2.py \
  v2/domain/tests/test_scene_grounding.py \
  v2/domain/tests/test_perception_audibility.py \
  v2/domain/tests/test_continuity_mutation_pipeline.py -q                                   → 114 passed
python -m pytest v2/domain/tests/ -q                                                        → 554 passed
```

**Documentation gap (non-blocking):** `PACKET_CONTRACTS.md` does not yet mention optional `occurrence_evidence`; `GLOSSARY.md` and `docs/story-knowledge.md` updated. Remediate before closure if Governance requires packet-level parity.

**Issue transition:** [Validation comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450158856)

## Post-validation remediation (audit observability + documentation)

**Governance finding (2026-08-28):** Product semantics validated at `9d9204148300afd2797fc243350ea012f1c2ec90`; closure blocked pending explicit audit projections for summary selection and #50 committed-text composition. Status reverted to `implemented` for bounded remediation ([workflow comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450355924)).

### Required observability additions

| Field | Location | Purpose |
|-------|----------|---------|
| `summary_selection_source` | `turn_metadata_by_index[turn_index]` | Explicit branch that selected promoted `summary` |
| `evidence_projection` | `StoryKnowledgeRecord` JSONL | Globally projected component manifest + scoped-exclusion flags |

**`summary_selection_source` values:** `character_action`, `character_dialogue`, `character_action_and_dialogue`, `director_environment`, `state_change_fallback`, `default_fallback`, `grounding_markers`.

**`evidence_projection`:** `{ source_event_id, projection_sources[], scoped_evidence_present, scoped_evidence_projected }` — no restricted content in manifest.

**Out of scope:** per-query Retrieval/Librarian candidate ledger; parallel #51 audit log; promotion coverage change.

**Documentation:** authoritative docs updated per pre-closure investigation inventory (`GLOSSARY.md`, `docs/story-knowledge.md`, `docs/architecture.md`, `docs/rp-data-layout.md`, `PACKET_CONTRACTS.md`, `CANONICAL_KNOWLEDGE_MODEL.md`, `docs/forensic-auditability-standard.md`, `docs/audit-workflows.md`, `governance/sources/architecture-overview.md`).

**Revalidation:** completed at `e3ff28db08deb3ebcdf5b4f7df58a0b965fd1138` ([comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450420444)).

## Closure (2026-08-28)

| Field | Value |
|-------|-------|
| Assigned / effective weight | `standard` / `full` |
| Bootstrap profile | Full |
| Baseline anchor | `356a0b28adc656ac52a96a3e8cb48481178cd048` |
| Primary implementation SHA | `6cec5938dc54273176dfa592a89e881d30d63236` |
| First validation anchor | `9d9204148300afd2797fc243350ea012f1c2ec90` |
| Audit/docs remediation SHA | `0a2a615805213e5d2192d67c6af04b99e46e3a0b` |
| Final revalidation product anchor | `e3ff28db08deb3ebcdf5b4f7df58a0b965fd1138` |
| Final integrated SHA | *(recorded at push — see Issue closure comment)* |
| Full revalidation | **565 passed** (`v2/domain/tests/`) |
| Documentation remediation | complete (9 authoritative docs) |
| Auditability remediation | `summary_selection_source` + `evidence_projection` |
| Architecture conformance | PASS |
| #49 | unchanged, parked |
| #50 | unchanged, closed |

**Deferred boundaries (not new Issues):** per-query Retrieval candidate ledger; promotion-coverage expansion; Narrator B2/C establishment (#49).

**Issue transition:** *(closure comment permalink recorded post-close)*

## Chronology

| Stage | Anchor / record | Status |
|-------|-----------------|--------|
| Initial implementation | `6cec5938dc54273176dfa592a89e881d30d63236` | complete |
| First Full validation | `9d9204148300afd2797fc243350ea012f1c2ec90` | PASS (2026-08-28) |
| Pre-closure conformance investigation | [comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450281251) | audit/docs gaps identified |
| Governance-required remediation | `0a2a615805213e5d2192d67c6af04b99e46e3a0b` | `summary_selection_source` + `evidence_projection` + docs |
| Workflow rollback | [comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450355924) | `validated` → `implemented` |
| Forensic SHA note | `e3ff28db08deb3ebcdf5b4f7df58a0b965fd1138` | docs-only |
| **Full revalidation** | `e3ff28db08deb3ebcdf5b4f7df58a0b965fd1138` | **PASS** (2026-08-28) |

## Revalidation (post-remediation)

**Revalidation anchor:** `e3ff28db08deb3ebcdf5b4f7df58a0b965fd1138`

**Scoped diff (remediation):** `9d92041` → `e3ff28d` — audit observability + documentation + tests + forensic record only.

**Determination:** PASS — semantic contract + forensic reconstructability

| Area | Result |
|------|--------|
| Original #51 semantic contract | PASS (reconfirmed) |
| `summary_selection_source` provenance | PASS |
| `evidence_projection` manifest fidelity | PASS |
| Composition manifest vs `committed_text` | PASS |
| Forensic reconstruction join (no reverse-engineering) | PASS |
| Epistemic (no audit-metadata leakage) | PASS |
| Idempotency / legacy compatibility | PASS |
| Documentation conformance (9 docs) | PASS |
| Forensic standard / audit-workflow recipe | PASS |
| Architecture conformance (12 questions) | PASS |

**Forensic reconstruction trace (representative):**

```text
domain_commit_id=hg-commit-forensic-1
  → turn_metadata_by_index[1].summary_selection_source=character_action_and_dialogue
  → PublicEvent event_id=evt_* turn_index=1
  → occurrence_evidence (contributions, triggering_user.entry_id=hist-u1, scoped_evidence)
  → StoryKnowledgeRecord (source_domain_commit_id, evidence_projection.projection_sources)
  → evidence.committed_text (globally eligible only)
```

**Commands at revalidation:**

```text
python -m pytest v2/domain/tests/test_issue_51_occurrence_evidence.py -q → 11 passed
python -m pytest v2/domain/tests/test_issue_51_audit_provenance.py -q → 11 passed
python -m pytest v2/domain/tests/test_story_knowledge_issue_50.py -q → 17 passed
python -m pytest v2/domain/tests/ -q → 565 passed
```

**Issue transition:** [Revalidation comment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/51#issuecomment-5450420444)

## Rejected implementation alternatives

- Event-type-specific schema fields (`refusal_object`, etc.)
- Renaming `state_changes`
- Separate Issue for #50 adapter
- Copying full `structured_move` or Continuity registries onto `PublicEvent`
