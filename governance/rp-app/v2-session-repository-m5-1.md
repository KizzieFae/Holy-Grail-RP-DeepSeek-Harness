# V2 SessionRepository + Domain Host Skeleton — M5.1 Implementation Report

**Status:** Completed (M5.1 — repository-backed domain host skeleton)  
**Date:** 2026-08-17  
**Production boundary anchor:** `cf463cf`  
**Implementation HEAD:** (see §17 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

**Authorization boundary:** DSH `runRound()` default path unchanged. Production session lifecycle available via Domain Host HTTP; DSH cutover deferred to M5.2.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `cf463cf` |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 implementation |

Pre-slice validation: 37 Python + 30 Node tests green.

---

## 2. Real persistence contract preserved

V1 semantics wrapped (not Streamlit orchestration):

| V1 component | M5.1 usage |
|--------------|------------|
| `SessionManager` | File persistence under configurable `sessions_dir` |
| `ContinuityManager.to_dict()` / `from_dict()` | Authoritative continuity round-trip in `metadata.continuity_state` |
| `CharacterState.to_dict()` / `from_dict()` | `metadata.character_states` |
| Session file shape | `session_id`, `characters`, `team_state` (minimal V2 stub), `metadata` |
| Session index | Via `SessionManager._upsert_index_entry` on save |

**V2 host metadata extension** (`metadata.v2_host_state`):

- `committed_move_count`, `commit_ids`, `character_private_secrets`, `continuity_version`

**Session identity (M5.1):** `hg_session_id` ↔ `hg_scene_id` = **1:1** (matches V1 `session_id` file key).

---

## 3. SessionRepository architecture

**Module:** `v2/domain_api/session_repository.py`

| Responsibility | Owner |
|----------------|-------|
| Create/open session | `SessionRepository` |
| Live object cache | `_cache: dict[str, LiveSession]` |
| Serialize/deserialize | `_build_session_payload`, `_hydrate_session` |
| Synchronous persist | `persist()` → `SessionManager.save_session()` |
| Commit idempotency index | `_commit_dedup` (in-memory per process) |
| Manager rollback snapshot | `snapshot_manager` / `restore_manager` |

**Not owned by repository:** validation, eligibility, participation, context projection, DSH trace.

**Live session type:** `LiveSession` in `session_state.py` — `ContinuityManager`, `CharacterState` map, round fixtures (ephemeral), host counters.

---

## 4. DomainKernel integration

```text
DomainKernel
    ↓ injected store
SessionRepository (production default) | FixtureStore (tests only)
```

- `DomainKernel(repository=...)` or `DomainKernel(store=FixtureStore())` for tests
- All domain operations unchanged; `store.require(hg_scene_id)` supplies `LiveSession`
- `create_session()` / `open_session()` return `SessionInfoResponse`
- `create_scene()` retained as **transitional** alias → `create_session()`

---

## 5. Session lifecycle

| Endpoint | Behavior |
|----------|----------|
| `GET /health` | `{ "status": "ok" }` when repository initialized |
| `POST /v1/sessions/create` | Create + persist; returns `SessionInfoResponse` |
| `POST /v1/sessions/open` | Load from disk + cache; returns current metadata |
| `POST /v1/scenes` | **Transitional** — alias to create; removal when DSH uses sessions API |

---

## 6. Commit durability semantics

```text
validate → process_turn → update live session → persist() → committed=true
```

`committed=true` guarantees continuity mutation **and** session file written.

`continuity_version` increments on each successful persist.

---

## 7. Persistence failure semantics

On `persist()` failure (`PersistenceError`):

1. Restore `ContinuityManager` from pre-commit snapshot
2. Restore round fixture fields from snapshot
3. Restore `committed_move_count` / `commit_ids`
4. Return `committed=false` with reason

Live and persisted state remain coherent.

---

## 8. Idempotency / staleness

- Dedup key: `(hg_scene_id, inference_id, expected_turn_index, character_id, move fingerprint)`
- Checked **before** turn-index anchor — safe retry after successful commit
- Replay returns original `CommitResponse` including `domain_commit_id`
- Stale `expected_turn_index` still rejected for non-replay commits

---

## 9. Restart persistence proof

`test_session_repository.py::test_commit_survives_repository_restart`:

1. Create session → commit move → persist
2. `repository.clear_cache()` + new `SessionRepository` instance
3. `open_session` → `turn_counter == 1`, `committed_move_count == 1`

---

## 10. FixtureStore retirement

| Item | Status |
|------|--------|
| `FixtureStore` | **Test-only** — explicit `DomainKernel(store=FixtureStore())` in domain tests |
| Production `DomainKernel()` default | `SessionRepository` |
| `create_prototype_scene` | Moved to `session_state.initialize_live_session` |
| Prototype in-memory production path | **Superseded** |

---

## 11. Production HTTP skeleton

**Module:** `v2/domain_api/http_transport.py` (localhost production skeleton)

- Bind restricted to `127.0.0.1` / `localhost` / `::1`
- `__main__.py` starts `SessionRepository` + `DomainKernel` (no auto scene on boot)
- Existing round/context/validate/commit routes unchanged

---

## 12. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python (`pytest v2/tests`) | **44 passed** (incl. 7 new repository tests) |
| V2 Node (`npm test`) | **30 passed** |
| DSH default path | Unchanged — still uses `POST /v1/scenes` via transitional endpoint |

---

## 13. Clean-V2 review

| Classification | Items |
|----------------|-------|
| **Permanent** | `SessionRepository`, `session_state.LiveSession`, repository-injected `DomainKernel`, sync commit persist, `/health`, `/v1/sessions/*` |
| **Test-only** | `FixtureStore` |
| **Transitional** | `POST /v1/scenes`, `create_scene()` alias |
| **Superseded** | FixtureStore as production authority, `__main__` auto scene creation |

---

## 14. Domain Host assessment

Python side now matches bounded domain host:

```text
Domain Host
  ├── SessionRepository (persistence)
  ├── DomainKernel (operations)
  ├── ContinuityManager (authority)
  ├── validation / eligibility / participation / context (kernel)
  └── HTTP adapter (localhost)
```

Does **not** own: DSH orchestration, providers, UI state, execution trace.

---

## 15. Challenge / refinement

| Question | Finding |
|----------|---------|
| Meaningful permanent boundary? | Yes — single persistence path via V1 `SessionManager` |
| FixtureStore left production? | Yes — default is `SessionRepository` |
| `committed=true` durable? | Yes — tested + rollback on failure |
| Persistence failure coherent? | Yes — manager + round + host counters restored |
| Commit retries idempotent? | Yes — dedup before anchor check |
| Restart recovery? | Yes — integration test |
| Independent of Streamlit? | Yes |
| Session identity clean? | 1:1 documented |
| Domain API semantics preserved? | Yes — all prior tests green with `FixtureStore` |
| Second session model? | No — one `LiveSession` type |
| Closer to clean V2? | Yes |

---

## 16. Architecture verdict

**validated as designed**

One note: commit dedup index is process-local; durable idempotency across host restart can use persisted `commit_ids` in a future slice if needed.

---

## 17. Repository state

| Field | Value |
|-------|-------|
| Implementation HEAD | (after commit) |
| `origin/main` | pushed |

---

## 18. Next recommended slice

**M5.2 — DSH production session cutover** (Governance review required):

1. Add `sessions/create` or `sessions/open` to `domain-api-client.mjs`
2. Switch `HgRoundOrchestrator.runRound()` to require `hgSessionId` or call production create
3. Retire default `POST /v1/scenes` from orchestrator path
4. Correlate `hg_session_id` in `HgTraceEmitter` payloads
5. Integration test: full round via production session lifecycle + restart mid-session

**Out of scope:** launcher, gRPC, Streamlit rewiring, knowledge DB.
