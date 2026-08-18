# V2 DSH Production Session Cutover — M5.2 Implementation Report

**Status:** Completed (M5.2 — DSH production session lifecycle cutover)  
**Date:** 2026-08-17  
**M5.1 SessionRepository anchor:** `0d5eec1`  
**Implementation HEAD:** (see §16 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `0d5eec1` |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |

Pre-slice: 45 Python + 30 Node tests green.

---

## 2. Production session client

**`domain-api-client.mjs`** additions:

| Method | Endpoint |
|--------|----------|
| `health()` | `GET /health` |
| `createSession(body)` | `POST /v1/sessions/create` |
| `openSession(hgSessionId)` | `POST /v1/sessions/open` |

`createScene()` retained as **deprecated transitional** for direct HTTP tests only; production orchestration no longer calls it.

**`resolve-round-session.mjs`** — explicit session resolution:

- `{ mode: 'create', cast?, location?, hg_session_id? }`
- `{ mode: 'open', hg_session_id }`

---

## 3. HgRoundOrchestrator cutover

**Before:** `api.createScene()` when `hgSceneId` absent.

**After:** `resolveRoundSession(api, options)` — **required** `options.session` with explicit mode.

Production flow:

```text
runRound({ session: { mode: 'create' | 'open', ... } })
    → createSession | openSession
    → hg_session_id / hg_scene_id (1:1)
    → startRound → phases → commit (persisted)
```

Round result now includes: `hg_session_id`, `continuity_version`.

**DSH execution session:** unique per `runRound()` invocation (`hg-exec-{uuid}`), correlated to durable HG session via `hg_session_id` in trace.

---

## 4. Session identity / correlation

| ID | Role |
|----|------|
| `hg_session_id` | Durable authoritative identity (1:1 with `hg_scene_id`) |
| `hg_scene_id` | Domain API scene scope |
| `dsh_scene_session_id` | Ephemeral execution evidence per orchestrator run |
| Inference `SessionId`s | Per Director/Character/Narrator inference |

**HgTraceEmitter.correlation()** now includes `hg_session_id`.

---

## 5. Durable round proof

`production-session-round.test.mjs`:

- Full round via `sessions/create` → commit → session file on disk
- Boundary metrics include `createSession`, not `createScene`
- `hg/round-started` carries `hg_session_id`

---

## 6. Domain Host restart / resume

Same test file:

```text
create → round 1 → kill host → new host (same HG_SESSIONS_DIR)
    → open session → round 2 → continuity_turn_index == 2
```

---

## 7. DSH restart proof

New Cordis context + new `dsh_scene_session_id`; same `hg_session_id`; persisted `turn_counter` unchanged.

---

## 8. Idempotency across restart

**Python:** `commit_dedup_index` persisted in `metadata.v2_host_state`; restored on `open_session`.

**Test:** `test_commit_dedup_survives_repository_restart`

Commit order fixed: record dedup → persist (dedup included in file).

---

## 9. Traceability

Trace events carry `hg_session_id`, `hg_scene_id`, `hg_round_id`, `dsh_scene_session_id` — sufficient to reconstruct session → round → inference → commit chain.

---

## 10. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python | **45 passed** |
| V2 Node | **35 passed** (incl. 3 production-session tests) |
| Live tests | Run when `DEEPSEEK_API_KEY` set (unchanged path via `session: { mode: 'create' }`) |

Tests run sequentially (`--test-concurrency=1`) for reliable Domain Host startup.

---

## 11. Transitional lifecycle retirement

| Artifact | Status |
|----------|--------|
| `createScene()` in orchestrator | **Removed** |
| `createScene` in domain client | **Deprecated** (test-only) |
| `POST /v1/scenes` | **Transitional** — HTTP compatibility; not production orchestration |
| `FixtureStore` | **Test-only** (Python unit tests) |

---

## 12. Clean-V2 review

| Classification | Items |
|----------------|-------|
| **Permanent** | SessionRepository, sessions/create/open, hg_session_id correlation, production orchestrator path |
| **Test-only** | FixtureStore, deprecated createScene client method |
| **Transitional** | `POST /v1/scenes` — remove when no test depends on it |
| **Superseded** | Production prototype scene lifecycle in DSH |

---

## 13. Mature architecture assessment

- DSH operates against persistent SessionRepository-backed Domain Host
- Python host restart preserves committed state
- DSH restart independent (new execution session, same HG session)
- Single authoritative session identity (`hg_session_id`)
- HTTP is intentional production boundary
- FixtureStore not in production path

**Remaining transitional boundary:** launcher/process supervision; optional removal of `POST /v1/scenes`.

---

## 14. Challenge / refinement

| Finding | Resolution |
|---------|------------|
| Both session models alive? | No — orchestrator requires explicit session mode |
| DSH session ID on resume? | Unique per runRound; HG ID in trace |
| Dedup across restart? | Persisted in v2_host_state |
| Test flakiness? | Sequential test concurrency + health-based startup helper |

---

## 15. Architecture verdict

**validated as designed**

---

## 16. Repository state

Committed and pushed after implementation.

---

## 17. Next recommended slice

**M6 — Domain Host launcher / supervised startup** (Governance review required):

1. Single entrypoint starts Domain Host (health wait) then DSH runtime
2. `HG_DOMAIN_HOST_URL` env wiring in bootstrap
3. Optional Streamlit/UI consumer stub using `sessions/open`
4. Retire `POST /v1/scenes` from remaining tests

**Out of scope:** knowledge DB, UI rewiring, multi-scene-per-session.
