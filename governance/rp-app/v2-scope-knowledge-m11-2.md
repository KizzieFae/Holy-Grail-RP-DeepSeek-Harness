# V2 Scope Knowledge — M11.2 Implementation Report

**Status:** Completed (M11.2 — learned world knowledge + user profile)  
**Date:** 2026-08-18  
**M11.1 anchor:** `83567f3`  
**M11 architecture anchor:** `5d1aa26`  
**Implementation HEAD:** (see §22 after commit)

---

## 1. Scope

Extend permanent `KnowledgeService` with two durable, scope-bound lanes behind the existing M11.1 seam:

| Lane | Source | Promotion |
|------|--------|-----------|
| `learned_world_knowledge` | Canon anchors `category=world_fact` after successful domain commit+persist | Automatic via `KnowledgeWritePolicy` |
| `user_profile` | Explicit structured API only | `set_user_profile_fact` / `POST /v1/sessions/user-profile` |

**Governance:** `scope_id = session.memory_scope_id` for M11.2. APIs use neutral `scope_id`; no second world/knowledge scope ID introduced.

**Not in scope:** M11.3 scene grounding, vectors/SQLite, V1 bucket migration, regex preference harvest, DSH changes.

---

## 2. V1 behavior preserved/rejected

### World facts — preserved semantics

- Durable truths from continuity canon anchors tagged `world_fact`
- Scope-bound recall (not global broadcast)
- Deterministic caps and ordering
- Reference/suggestive authority (not independent canon)

### World facts — rejected mechanisms

- Save-time `persistent_world_facts` bucket copying
- Location-string auto-promotion without anchor
- Session-summary aggregation
- Cross-session global broadcast to all casts

### User preferences — preserved semantics

- Stable player-dimension facts (`preferred_name`, `interaction_preference`)
- Scope-bound retrieval for orchestration/character context

### User preferences — rejected mechanisms

- `extract_user_preferences` regex on chat
- `"User goes by {name}"` speaker-plumbing fallback
- Global broadcast to every role prompt

---

## 3. KnowledgeWritePolicy architecture

| Module | Role |
|--------|------|
| `v2/domain_api/knowledge_write_policy.py` | Classify/promote `learned_world_knowledge`, build explicit `user_profile` records |
| `v2/domain_api/knowledge_service.py` | Orchestrate promotion, retrieval, ContextAssembly projection |

**Owns:** eligibility, authority class, scope assignment, visibility, provenance, stable IDs  
**Does not own:** Continuity mutation, memory writes, model inference, DSH, UI, semantic ranking

---

## 4. Scope-backed KnowledgeRepository

| Module | Storage |
|--------|---------|
| `v2/domain_api/scope_knowledge_repository.py` | JSON per `scope_id` under `sessions_dir/_scope_knowledge/` |

```
KnowledgeService
    ├── AuthoredKnowledgeProvider (M11.1 — snapshot compile)
    └── ScopeKnowledgeRepository (M11.2)
           ├── learned_world_knowledge
           └── user_profile
```

Idempotent upsert by `knowledge_id`; user profile upsert by `(scope_id, profile_key, user_persona_id)`.

---

## 5. Learned world-fact policy

Promotion requires:

- Successful domain commit + session persist
- Canon anchor with `category=world_fact` and non-empty `statement`
- `scope_id` from `memory_scope_id`
- Provenance: `source_kind=canon_anchor`, `source_domain_commit_id`, `source_continuity_anchor_id`

**Does not promote:** moves, location strings alone, transcripts, MemoryService records, narrator prose, session summaries.

Visibility:

- `scope_global` when anchor `subject` is not a cast member name
- `character_scoped` when `subject` matches a cast character (world truth about that character; not automatic character memory)

---

## 6. User-profile policy

Whitelist keys: `preferred_name`, `interaction_preference`

Explicit API only — no regex/chat auto-promotion. Visibility: `scope_global` within scope (player dimension, not world canon).

---

## 7. Authority/precedence behavior

| Layer | Authority |
|-------|-----------|
| `scene_state` | `authoritative` (priority 10) |
| Authored / learned / user profile | `suggestive` (priority 21+) |
| Character memory | `derived` (priority 26+) |

Continuity remains canonical. Learned facts carry `authority_note: reference_derived_from_continuity_not_independent_canon`.

**Supersession:** On retrieve, if current session has the linked anchor with a different statement, stored learned fact is suppressed. Re-commit after anchor change upserts stored content by stable `knowledge_id`. If anchor absent in a new session, scope-persisted reference remains visible (cross-session scope recall).

---

## 8. Visibility/privacy behavior

- Character-scoped learned facts reach only the matching `subject_character_file_id`
- Scope-global learned facts reach all characters in scope
- User profile projected as separate `user_profile` lane (not merged with memory)
- M11.1 authored/private lanes unchanged

---

## 9. Promotion transaction/failure semantics

```
domain commit succeeds → session persist succeeds → KnowledgeService.promote_after_commit (best-effort)
```

Knowledge persist failure does **not** roll back domain commit. Failures logged at warning level (mirrors M10.2 cross-scope memory posture).

---

## 10. Idempotency/revision behavior

- `knowledge_id = hash(scope_id, lane, anchor_id)` for learned world facts
- `knowledge_id = hash(scope_id, user_profile, profile_key, user_persona_id)` for profile facts
- Retry/restart does not duplicate records
- Anchor content updates upsert by `knowledge_id`

---

## 11. ContextAssembly integration

Lanes (distinct provenance, ordered):

1. `authored_character_knowledge` (M11.1)
2. `scene_reference` (M11.1)
3. `learned_world_knowledge` (M11.2, cap 8)
4. `user_profile` (M11.2, cap 6)

Separate from `character_memory`, `scene_state`, `character_private`.

---

## 12. Scope isolation proof

Tests: `test_scope_isolation_between_memory_scopes` — same cast/card, different `memory_scope_id`, facts do not cross.

---

## 13. Character/privacy proof

Tests: `test_character_scoped_world_fact_visibility` — Alice-scoped anchor not visible to Bob.

---

## 14. Persistence/restart proof

Tests: `test_learned_knowledge_survives_repository_restart` — Session A promotes; repository restart; Session B same scope retrieves learned fact.

---

## 15. MemoryService separation proof

Tests: `test_explicit_user_profile_write_and_retrieval` — `CharacterState` unchanged after profile write. No automatic memory promotion from knowledge retrieval.

---

## 16. V1 bucket retirement impact

| V1 | V2 replacement | Status |
|----|----------------|--------|
| `persistent_world_facts` | `learned_world_knowledge` via canon anchor promotion | **Replaced in V2** |
| `user_preferences` regex bucket | `user_profile` explicit API | **Replaced in V2** |
| Save-time bucket copy | Scope repository + commit hook | **Superseded** |

V1 code retained until broader retirement authorization.

---

## 17. Scope-future assessment

**One continuity scope remains sufficient.** No product evidence yet for splitting `memory_scope_id` from a separate world/knowledge scope. Future split justified only if product requires shared world knowledge with isolated character memory — not demonstrated.

---

## 18. Behavioral validation

```text
python -m pytest v2/tests/ -q  → 84 passed
cd v2/rp_runtime && npm test   → 51 passed
```

New: `v2/tests/test_scope_knowledge_m11_2.py` (10 tests). M11.1 regression: 7 tests green.

---

## 19. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `KnowledgeWritePolicy`, `ScopeKnowledgeRepository`, learned/profile lanes, `KnowledgeService` integration, commit promotion hook, user-profile API |
| **Reused** | M11.1 authored provider, canon anchor evidence, `memory_scope_id` |
| **Superseded** | V1 world-fact buckets, regex preference broadcast, cross-session bucket loading |
| **Deferred** | vectors, SQLite, graph, knowledge tools, learned episodic retrieval, M11.3 scene grounding |
| **Test-only** | Synthetic anchor/profile fixtures in M11.2 tests |

---

## 20. Challenge/refinement

| Question | Answer |
|----------|--------|
| Second canon store? | **No** — reference persistence with explicit suggestive authority |
| Appropriate promotion only? | **Yes** — `world_fact` anchors only |
| User prefs too aggressive? | **No** — explicit whitelist API only |
| Distinct from memory? | **Yes** — no CharacterState writes |
| Scope boundaries? | **Yes** — scope_id keyed |
| Privacy leaks? | **No** — character_scoped filter enforced |
| Continuity overrides stale? | **Yes** — anchor statement mismatch suppresses |
| Idempotent? | **Yes** |
| Backend replaceable? | **Yes** — repository behind service seam |
| V1 buckets renamed? | **No** — explicit new lanes |
| One scope sufficient? | **Yes** |
| Vectors needed? | **No** |
| M11.3 next? | **Yes** — scene/canon-context grounding |

---

## 21. Architecture verdict

**Validated with refinements:**

- Cross-session scope recall retains persisted facts when anchor not re-established in new session (reference posture)
- Anchor statement change requires re-commit to refresh stored content (minimal upsert, not full version control)

---

## 22. Next recommended migration slice

**M11.3 — scene grounding / canon-context** (investigation + implementation per Governance). Do not implement without Governance review.
