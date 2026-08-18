# V2 Retrieval-Index Capability — M12.7

**Status:** Complete  
**Date:** 2026-08-18  
**M12.6 anchor:** `2e9cbf4`  
**M12.7 completion HEAD:** `1f6a34c`

**Objective:** Migrate useful V1 retrieval-index behavior into permanent V2 KnowledgeService / ContextAssembly without resurrecting deleted V1 prompt runtime.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `2e9cbf4` |
| `origin/main` | aligned at activation |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

### Validation

| Suite | Pre-slice | Post-slice |
|-------|-----------|------------|
| V2 Python | 122 passed, 1 xfailed | **129 passed, 1 xfailed** |
| V2 Node | 55 passed | **55 passed** |
| Neutral domain | 358 passed | **358 passed** |

---

## 2. Reconstructed V1 retrieval behavior

| V1 mechanism | Useful semantics |
|--------------|------------------|
| `authored_retrieval_index` + `RP_RETRIEVED_CONTEXT_INDEX` | Precompiled authored reference corpus |
| `authored_index_compile` + `canonical_compile_adapters` | Deterministic asset → record compile |
| `retrieved_selection_authored` | Lane ordering, tag/template relevance |
| `retrieved_context_select` | Visibility filter, per-kind caps, global 8 items / 8000 chars |
| `prompt_retrieval_assembly` | Inject retrieved bundle into character prompts |
| `retrieved_episodic_merge` | Merge episodic with authored under global cap |
| Feature flag env | Optional compiled index activation |

---

## 3. Retained / replaced / rejected semantics

| Semantics | V2 status |
|-----------|-----------|
| Authored character lore lookup | **Retained** — M11.1 snapshot + selection |
| Template premise/tone/opening reference | **Retained** — M11.1 |
| Template `role_slots` reference | **Retained** — M12.7 snapshot compile |
| Compiled index supplement | **Retained** — `CompiledIndexRetrievalProvider` |
| Deterministic caps/dedupe | **Retained** — `retrieval_selection.py` |
| Visibility before model exposure | **Retained** — enforced in selection |
| Direct prompt injection / V1 assembly | **Rejected** — KnowledgeService → manifest only |
| Omniscient/global weak retrieval | **Rejected** |
| Episodic retrieval in KnowledgeService | **Rejected/deferred** — MemoryService owns episodic |
| Vector/embedding retrieval | **Rejected** — no product evidence |

---

## 4. Retrieval corpus model

### Session-snapshot corpus (frozen at create)
- `character_cards[*].lore_facts`
- `scene_template.{premise,tone,opening_text,role_slots}`
- Scoped by `setup_snapshot`; immutable across reopen

### Optional global compiled corpus
- Precompiled JSON index (v3 schema)
- Activated via `HG_RETRIEVAL_INDEX_PATH` or legacy `RP_RETRIEVED_CONTEXT_INDEX`
- Example: `autogen_rp/python/data/retrieval/compiled/operational_pilot_v3.json`
- Live/evolving; session snapshot wins on `knowledge_id` collision

### Explicitly excluded
- Continuity canon, scene grounding, MemoryService episodic, `rp_history`, DSH logs

---

## 5. RetrievalProvider architecture

```text
setup_snapshot compile (authored_knowledge.py)
        +
optional CompiledIndexRetrievalProvider.query
        ↓
merge_authored_record_sets (snapshot precedence)
        ↓
select_retrieval_records (visibility + caps)
        ↓
KnowledgeService.project_context
        ↓
PromptContributionManifest → HgContextBridge → DSH
```

Provider does **not** own authority, privacy policy, continuity, or memory.

---

## 6. Record/index contract

Reuses `AuthoredKnowledgeRecord`:

- `knowledge_id`, `knowledge_kind`, `content`, `authority_class`, `visibility`
- `subject_character_file_id`, `source_kind`, `source_asset_id`, `provenance`
- Index chunks map through canonical authority → V2 `suggestive` reference class

---

## 7. Query model

Structured `RetrievalQueryContext`:

- `character_file_id`, `character_display_name`
- `character_index_keys` (file id + normalized display aliases)
- `session_template_id`

No LLM-generated query terms.

---

## 8. Deterministic filtering/ranking

Order in `select_retrieval_records`:

1. Visibility filter (`character_scoped`, `template_participants`, `public`)
2. Dedupe by `knowledge_id`
3. Lane priority: `scene_reference` before `authored_character_knowledge`
4. Stable `source_index` ordering
5. Per-lane caps (4 character / 3 scene)
6. Global caps (8 items / 8000 chars)

---

## 9. Authority/visibility behavior

- Retrieved material remains **suggestive** reference (`authority_class=suggestive`)
- Live continuity / scene_state remain authoritative
- Character-scoped records require matching `character_file_id`
- Template records require matching `session_template_id`
- Relevance never upgrades authority

---

## 10. KnowledgeService integration

`KnowledgeService.retrieve_authored` now:

1. Compiles snapshot records
2. Queries optional compiled index
3. Merges with snapshot precedence
4. Applies deterministic selection
5. Exposes `retrieval_diagnostics` in manifest provenance

---

## 11. M11.1 duplication decision — **Option B**

- M11.1 snapshot lanes remain the session-bound canonical source
- Compiled index **supplements** non-overlapping reference material
- Snapshot wins on `knowledge_id` collision
- Same manifest lanes (`authored_character_knowledge`, `scene_reference`) — no duplicate injection path

---

## 12. Episodic retrieval decision

**Deferred/rejected** for M12.7. Episodic material remains in MemoryService (`character_memory` lane). No merge with authored index in this slice.

---

## 13. Index lifecycle/persistence

- Snapshot corpus: compiled on demand from `setup_snapshot` (session-stable)
- Compiled index: lazy-loaded from file path; rebuildable derived artifact
- In-memory cache per provider instance; cleared on `clear_cache()`
- No durable index truth store introduced

---

## 14. Failure semantics

| Failure | Behavior |
|---------|----------|
| Missing/malformed index file | Log warning; supplemental query returns `[]`; session continues |
| Snapshot compile failure | Propagates (session setup already validated) |
| Mandatory visibility context | Enforced before manifest — no cross-character leakage |

---

## 15. Provenance/diagnostics

`RetrievalDiagnostics` in manifest provenance:

- `provider_id`, `index_path`, `setup_snapshot_hash`
- `candidate_count`, `visibility_dropped`, `dedupe_dropped`, `cap_dropped`
- `selected_ids`, `selected_character_count`, `selected_scene_count`, `total_chars`

---

## 16. Token budgeting

| Limit | Value |
|-------|-------|
| Character items | 4 |
| Scene reference items | 3 |
| Lore excerpt chars | 600 |
| Global items | 8 |
| Global chars | 8000 |

---

## 17–19. Proofs (tests)

| Proof | Test |
|-------|------|
| Character isolation | `test_multi_character_isolation_with_compiled_index` |
| Template role slots | `test_template_role_slots_reach_scene_reference_lane` |
| Snapshot stability | `test_snapshot_stability_after_source_edit` |
| Compiled index supplement | `test_compiled_index_supplements_without_duplicating_snapshot_lore` |
| Real card/template | celina + kizzie/willow integration in M12.7 + M11.1 suites |
| Caps | `test_global_caps_are_enforced` |

---

## 20. V1 parity matrix

| V1 behavior | V2 replacement | Decision |
|-------------|----------------|----------|
| Compiled authored index | `CompiledIndexRetrievalProvider` | Retained |
| Env activation flag | `HG_RETRIEVAL_INDEX_PATH` | Retained |
| Canonical compile adapters | `canonical_compile_adapters` + snapshot/index compile | Retained |
| Lane caps / global cap | `retrieval_selection.py` | Retained |
| Prompt retrieval assembly | `KnowledgeService.project_context` | Redesigned |
| Episodic merge | MemoryService only | Rejected in M12.7 |
| Live card scanning | Snapshot at create | Replaced |
| Vector search | — | Rejected |

---

## 21. Product-completion impact

**Is retrieval-index still a blocker?** **No.**

Remaining required gaps: player/settings UX. Optional: narrator semantic retry, audit/debug UI.

---

## 22. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `retrieval_selection.py`, `compiled_index_provider.py`, KnowledgeService merge, role_slots snapshot compile |
| **Reused** | `AuthoredKnowledgeRecord`, `canonical_compile_adapters`, M11 KnowledgeService |
| **Rejected** | V1 `prompt_retrieval_assembly`, episodic-in-index, vectors |
| **Deferred** | `SemanticRetrievalProvider`, model-callable search tools |
| **Test-only** | operational_pilot_v3 fixture in tests |

---

## 23. Architecture verdict

**Validated with refinements** — hybrid snapshot + optional compiled index; episodic and vectors explicitly deferred.

---

## 24. Next recommended slice

**M12.8 — Player/settings UX** (governance review before implementation).

---

## 25. Key files

| Path | Role |
|------|------|
| `v2/domain_api/retrieval_selection.py` | Deterministic filter/rank/caps |
| `v2/domain_api/compiled_index_provider.py` | Compiled index loader/query |
| `v2/domain_api/authored_knowledge.py` | Snapshot compile (+ role_slots) |
| `v2/domain_api/knowledge_service.py` | Orchestration + diagnostics |
| `v2/tests/test_retrieval_index_m12_7.py` | M12.7 proofs |

---

## 26. Repository state

| Field | Value |
|-------|-------|
| Commit | `1f6a34c` — `feat(v2): migrate retrieval-index capability (M12.7)` |
| Branch | `main` |
| Pushed | `origin/main` |
| Working tree | clean |
