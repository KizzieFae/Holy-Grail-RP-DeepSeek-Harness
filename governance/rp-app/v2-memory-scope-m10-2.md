# V2 Memory Scope — M10.2 Implementation Report

**Status:** Completed (M10.2 — MemoryService + explicit `memory_scope_id` + cross-scope recall)  
**Date:** 2026-08-18  
**M10 investigation anchor:** `1a41571`  
**M10.1 anchor:** `418afa9`  
**Implementation HEAD:** (set at commit)

---

## 1. Scope

Introduce the permanent Domain Host `MemoryService` seam and the first controlled cross-session recall lifecycle:

- every production session persists a `memory_scope_id`;
- new sessions are **isolated by default** (unique scope unless caller supplies an existing one);
- explicit shared scopes permit deterministic file-backed cross-session recall;
- cross-scope subject identity is `memory_scope_id` + `subject_character_file_id`;
- M10.1 session-local memory behavior is preserved behind `MemoryService`;
- **no** vector/semantic retrieval, graph memory, or memory-management UI.

Governing architecture unchanged:

> **Memory informs inference; only continuity commit establishes canon.**

> **Python Domain Host owns memory semantics and persistence.**

> **DSH receives only projected memory context.**

---

## 2. MemoryService architecture

| Module | Role |
|--------|------|
| `v2/domain_api/memory_service.py` | Backend-independent orchestration: session-local writes, cross-scope projection/retrieval |
| `v2/domain_api/memory_scope.py` | Scope ID generation and resolution (`new_memory_scope_id`, `resolve_memory_scope_id`) |
| `v2/domain_api/cross_scope_memory_repository.py` | File-backed JSON store per `memory_scope_id` |
| `v2/domain_api/memory_write_policy.py` | M10.1 write policy (consumed by MemoryService) |
| `v2/domain_api/memory_retrieval.py` | M10.1 session-local episodic tail projection |
| `v2/domain_api/kernel.py` | Hooks: `record_user_turn` → cross-scope projection; `prepare_context` → multi-lane retrieval |
| `v2/domain_api/session_repository.py` | Owns `MemoryService` + `CrossScopeMemoryRepository` at `sessions_dir/_cross_scope_memory` |

### Storage lanes

```text
MemoryService
    ├── SessionCharacterStateAdapter (M10.1 via memory_write_policy / memory_retrieval)
    │      → session-local episodic + relationship history in CharacterState
    │
    └── CrossScopeMemoryRepository
           → projected cross-session user-relationship lines only
```

`MemoryService` does **not** own continuity truth, DSH, UI, model inference, or vector search.

---

## 3. `memory_scope_id` semantics

### Default (governance decision)

Cross-session memory is **opt-in by explicit continuity scope**.

When creating a session without an existing scope:

```text
memory_scope_id = newly generated durable ID (hg-memory-scope-{uuid})
```

That session does **not** automatically share memory with other sessions.

### Shared continuity

Two or more sessions share cross-session memory only when they deliberately reference the same `memory_scope_id`.

### Rejected default

V1 implicit shared-cast clustering is **not** reproduced as V2 default. Character overlap or matching display names alone must never cause cross-session sharing.

### Session open

Reopening restores persisted `memory_scope_id` from session metadata/setup provenance. Scope is never recalculated from current UI or cast.

---

## 4. Stable subject identity

Cross-scope durable memory is keyed by:

```text
memory_scope_id + subject_character_file_id
```

Canonical in-session `actor_id`/display name remains separate. `character_file_ids` map display name → file stem at session create (M9 snapshot semantics).

---

## 5. Cross-scope storage model

- **Location:** `{sessions_dir}/_cross_scope_memory/{memory_scope_id}.json`
- **Record fields:** `memory_id`, `memory_scope_id`, `subject_character_file_id`, `memory_kind`, `content`, `authority_class=derived`, `source_session_id`, optional `source_domain_commit_id` / `source_hg_round_id`, `user_persona_id`, `created_at`, `provenance`
- **Idempotency:** `memory_id` = deterministic SHA-256 fingerprint of scope + subject + kind + source session + user + content
- **Ordering/cap:** sort by `created_at`, return last 8 records per subject/kind

---

## 6. Cross-scope write/projection policy

### Eligible for projection (M10.2 narrow lane)

| Projected | Not projected |
|-----------|---------------|
| New per-character user relationship history lines after perception-filtered user turn | Full `character_memory_summary` |
| | Full `recent_observations` episodic tails |
| | `private_memories` |
| | Transcripts, Narrator prose, DSH logs |
| | Character-turn memory (session-local only in M10.2) |

### Timing

```text
record_user_turn
    ↓
relationship history snapshot (before)
    ↓
MemoryService.write_user_turn_memory (session-local)
    ↓
SessionRepository.persist (authoritative)
    ↓
MemoryService.build_user_relationship_projection
    ↓
MemoryService.project_cross_scope_after_persist (best-effort)
```

**Failure policy:** session persist remains authoritative. Cross-scope projection failure is logged and retryable; it does **not** roll back session-local memory.

Character-turn commits (`commit_move`) continue M10.1 session-local writes only — no cross-scope projection in M10.2.

---

## 7. Session-local compatibility (M10.1)

Unchanged semantics behind `MemoryService`:

- character-turn memory on `commit_move`;
- perception-filtered user-turn memory;
- episodic tail retrieval (`memory_lane: session_local_episodic`);
- `authority_class: derived`;
- private-memory exclusion;
- restart survival via `CharacterState` persistence.

---

## 8–10. Isolation proofs (tests)

| Test | Invariant |
|------|-----------|
| `test_default_isolation_between_sessions` | Same character, different auto scopes → no cross recall |
| `test_explicit_shared_scope_recall` | Same scope + character → eligible memory recalled with provenance |
| `test_character_isolation_within_shared_scope` | Kizzie-only perception → Willow has no Kizzie cross-scope line |
| `test_same_cast_different_scopes_do_not_bleed` | Identical cast, different scopes → no bleed |
| `test_different_character_file_ids_remain_distinct` | Distinct `memory_id` per subject file ID |

Suite: `v2/tests/test_memory_scope_m10_2.py` (8 tests) + `v2/tests/test_session_memory_m10.py` (8 tests).

---

## 11. User-relationship recall

Cross-scope lane `memory_kind: cross_scope_user_relationship` projects new relationship history lines written during perception-filtered user turns. Retrieval excludes records from the **current** `source_session_id` (other sessions in the same scope only).

User identity uses existing turn `speaker` string (`user_persona_id`) — no new user identity system in M10.2.

---

## 12. ContextAssembly integration

`prepare_context` adds separate `character_memory` contributions per lane:

| Lane | `provenance.memory_lane` |
|------|--------------------------|
| Session-local episodic tail | `session_local_episodic` |
| Cross-scope relationship | `cross_scope_relationship` |

All contributions: `source_kind: character_memory`, `authority_class: derived`. Provenance preserves `memory_scope_id`, `subject_character_file_id`, `memory_ids`, `source_session_ids`.

---

## 13. Failure/idempotency behavior

- Duplicate projection retries: same `memory_id` skipped in repository append
- Repository restart: JSON files reload deterministically
- Repeated session open: scope unchanged
- Cross-scope projection: best-effort after successful session persist

---

## 14. Session/application API changes

| Surface | Change |
|---------|--------|
| `SessionCreateRequest.memory_scope_id` | Optional; Domain Host generates if omitted |
| `SessionInfoResponse.memory_scope_id` | Returned on create/open |
| `setup_snapshot.memory_scope_id` | Persisted provenance |
| `POST /v1/sessions` | Accepts `memory_scope_id` |
| `GET /v1/catalog/memory-scopes` | Safe metadata only (`memory_scope_id`) |
| `hg-application-client.mjs` | Passes `memory_scope_id` on create |
| Streamlit | Optional advanced scope text field |

Scope discovery UI deferred; explicit ID sufficient for integration testing.

---

## 15. V1 retirement impact

### Superseded for V2 path

| V1 artifact | V2 replacement | Removal condition |
|-------------|----------------|-------------------|
| `SessionManager.get_cross_session_memories()` cast-overlap aggregation | `MemoryService.retrieve_cross_scope_memory` with explicit `memory_scope_id` | V2-only deployments; no V1 session bridge |
| `load_cross_session_memories(st_module)` | Domain Host projection at user-turn persist | Streamlit V2 shell only |
| Streamlit cross-session memory cache | File-backed `CrossScopeMemoryRepository` | V1 UI path retired |
| Name-overlap scope inference | Explicit `memory_scope_id` at create | Governance default accepted |

V1 code retained; not broadly deleted in M10.2.

---

## 16. Validation

```text
python -m pytest v2/tests/ -q          → 67 passed
cd v2/rp_runtime && npm test           → 51 passed
```

No live DeepSeek call required for M10.2 acceptance.

---

## 17. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `MemoryService`, `memory_scope.py`, `CrossScopeMemoryRepository`, `memory_scope_id`, deterministic cross-scope retrieval, ContextAssembly multi-lane memory |
| **Superseded for V2** | Implicit cast-name scope, Streamlit cross-session caches, direct V1 aggregation in V2 |
| **Transitional** | V1 `get_cross_session_memories` (explicit removal conditions above) |
| **Test-only** | Synthetic scopes in `test_memory_scope_m10_2.py` |

---

## 18. Challenge/refinement

| Question | Verdict |
|----------|---------|
| Cross-session memory opt-in? | **Yes** — unique scope per session by default |
| Same-character sessions leak without shared scope? | **No** — proven by tests |
| Same-cast different scopes leak? | **No** — proven by tests |
| `character_file_id` stable enough? | **Yes** — M9 snapshot at create; rename does not rekey |
| MemoryService backend-independent? | **Yes** — repository injectable; session adapter separate |
| Session-local intact? | **Yes** — M10.1 tests green |
| Cross-scope projection narrow enough? | **Yes** — user-relationship lines only |
| Memories still derived? | **Yes** |
| Provenance sufficient? | **Yes** for M10.2 slice |
| User relationship recall correct? | **Yes** under explicit scope |
| Recreated V1 cache architecture? | **No** — file-backed scope store, no Streamlit cache |
| File store replaceable? | **Yes** — behind `MemoryService` |
| M10.3 still necessary? | **Yes** — vector/semantic retrieval and optional broader projection lanes remain out of scope |

---

## 19. Architecture verdict

**Validated with refinements** — MemoryService + explicit `memory_scope_id` architecture is sound. Refinements applied:

1. `memory_scope.py` extracted to break import cycle.
2. `role_assignments` applied to `scene_state` before continuity setup seam when no scene template (multi-character create fix).
3. Cross-scope projection limited to user-relationship history; character-turn cross-scope deferred.

---

## 20. Next recommended migration slice

**M10.3 — Cross-scope projection policy expansion (Governance review required)**

Evaluate whether additional V1-parity buckets (e.g. scoped world/session memory snippets) should project under explicit `memory_scope_id`, with continued exclusion of full episodic dumps and private material. Do **not** implement vector retrieval without separate governance approval.
