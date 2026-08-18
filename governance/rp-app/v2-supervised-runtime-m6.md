# V2 Supervised Runtime Startup — M6 Implementation Report

**Status:** Completed (M6 — supervised local runtime startup)  
**Date:** 2026-08-17  
**M5.2 production-session anchor:** `347abf5`  
**Implementation HEAD:** (see §16 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `347abf5` |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 implementation |

Pre-slice: 45 Python + 35 Node tests green at `347abf5`.

---

## 2. Previous startup model

| Mechanism | Classification |
|-----------|----------------|
| `python -m domain_api --host … --port …` (manual) | **Superseded** for production |
| Per-test `spawn(venvPython, …)` + `POST /v1/scenes` readiness probe | **Superseded** |
| `createHolyGrailRpContext({ domainApi: { baseUrl } })` with pre-started host | **Test-only** (via shared helper) |
| `tests/helpers/domain-api.mjs` duplicate spawn logic | **Superseded** → uses supervisor primitives |
| Streamlit / V1 launch paths | **Out of scope** (unchanged) |

---

## 3. Supervisor architecture

**Decision:** Node/TypeScript supervisor in `v2/rp_runtime/`.

**Rationale:** DSH/Cordis is the outer orchestration runtime; Python Domain Host is a supervised child process. The supervisor owns process lifecycle only — not RP semantics.

| Component | Path |
|-----------|------|
| CLI entrypoint | `v2/rp_runtime/bin/hg-runtime.mjs` |
| Supervisor | `v2/rp_runtime/src/runtime-supervisor/supervisor.mjs` |
| Domain Host process control | `v2/rp_runtime/src/runtime-supervisor/domain-host-process.mjs` |
| Runtime configuration | `v2/rp_runtime/src/lib/runtime-config.mjs` |
| Test helper (shared spawn) | `v2/rp_runtime/tests/helpers/domain-api.mjs` |

**Ownership:**

- **Supervisor:** Python resolution, spawn, health poll, DSH bootstrap, graceful shutdown, failure surfacing
- **Not supervisor:** sessions, rounds, provider policy, continuity, validation, UI

---

## 4. Startup flow

```text
HolyGrailRuntimeSupervisor.start()
    → reserve/spawn Domain Host (python -m domain_api)
    → poll GET /health until { service: "holy-grail-domain-host", status: "ok" }
    → set process.env.HG_DOMAIN_HOST_URL
    → createHolyGrailRpContext({ domainApi: { baseUrl } })
    → ready
```

DSH does not bootstrap production orchestration before Domain Host health passes.

---

## 5. Configuration

| Setting | Source | Default |
|---------|--------|---------|
| Domain Host URL | `HG_DOMAIN_HOST_URL` env (set by supervisor after spawn) | — |
| Explicit URL (attach mode) | `supervisor options.domainHostUrl` | — |
| Python executable | `HG_PYTHON_EXECUTABLE` | `autogen_rp/python/.venv/Scripts/python.exe` (Win) or `bin/python` |
| Sessions directory | `HG_SESSIONS_DIR` / spawn option | `autogen_rp/python/data/sessions` |
| Host bind | spawn option | `127.0.0.1` |
| Port | spawn option or dynamic (`reserveLocalPort`) | dynamic free port |

`createHolyGrailRpContext` reads `HG_DOMAIN_HOST_URL` via `resolveDomainHostUrl()` when `domainApi.baseUrl` is not passed explicitly.

---

## 6. Failure semantics

| Failure | Behavior |
|---------|----------|
| Python executable missing (absolute path) | Immediate structured error before spawn |
| Domain Host exits before healthy | Health wait throws; child terminated |
| Health timeout | Child terminated; no orphan |
| DSH bootstrap failure after host healthy | `supervisor.stop()` tears down Domain Host |
| Port conflict / wrong service on port | Health payload validation fails (`service` mismatch) |

---

## 7. Shutdown semantics

```text
SIGINT/SIGTERM (CLI) or supervisor.stop()
    → ctx.fiber.dispose()  (DSH runtime)
    → SIGTERM → SIGKILL Domain Host child
    → state = stopped
```

Committed session files are not mutated on shutdown.

---

## 8. Runtime crash behavior

| Event | Behavior (M6) |
|-------|----------------|
| Domain Host exits after startup | Supervisor does not auto-restart; new rounds fail at HTTP boundary; no false commits |
| DSH failure after startup | Domain Host state remains durable; supervisor can stop remaining child |

Full automatic Domain Host restart deferred.

---

## 9. `/v1/scenes` retirement

| Surface | Status |
|---------|--------|
| `POST /v1/scenes` | **Removed** from HTTP transport |
| `GET /v1/scenes/{id}/state` | **Transitional read-only** alias (Python tests / legacy) |
| `GET /v1/sessions/{id}/state` | **Production** session state route |
| `createScene()` in `domain-api-client.mjs` | **Removed** |
| `getSessionState()` | **Added**; `getSceneState()` delegates |
| Integration tests | Migrated to `sessions/create` + session state |
| Kernel `create_scene()` | **Python test-only** via FixtureStore |

No production DSH path uses `POST /v1/scenes`.

---

## 10. Windows validation

Validated on Windows 10 (user environment):

- Venv Python resolution via absolute path (`autogen_rp/python/.venv/Scripts/python.exe`)
- Repository path with spaces (`Holy Grail RP DeepSeek Harness`)
- Child process spawn, stdout/stderr pipes
- Health-gated readiness (no arbitrary sleep semantics in supervisor)
- Dynamic port allocation
- SIGTERM shutdown (exit via signal, not necessarily `exitCode === 0`)
- No orphan processes after failed startup (health timeout path) or `supervisor.stop()`
- Persisted sessions survive shutdown/relaunch (production-session restart tests)

---

## 11. Supervised production round proof

`tests/supervised-runtime-round.test.mjs`:

- `startSupervisedRuntime()` → full `HgRoundOrchestrator.runRound()` with `session: { mode: 'create' }`
- Durable `{sessionsDir}/{hg_session_id}.json` written
- Boundary metrics include `createSession`, not `createScene`

---

## 12. Validation

| Suite | Result |
|-------|--------|
| `cd v2 && python -m pytest -q` | **45 passed** |
| `cd v2/rp_runtime && npm test` | **40 passed** (incl. 4 supervisor + 1 supervised round) |
| Live DeepSeek (`DEEPSEEK_API_KEY`) | **passed** (`real-inference`, `real-full-round`) |

Commands:

```powershell
cd v2; python -m pytest -q
cd v2/rp_runtime; npm test
npm start   # supervised runtime CLI (Ctrl+C to stop)
```

---

## 13. Clean-V2 review

### Permanent

- `HolyGrailRuntimeSupervisor` + `bin/hg-runtime.mjs`
- `runtime-config.mjs` / `HG_DOMAIN_HOST_URL`
- Health-gated startup (`service: holy-grail-domain-host`)
- Production session lifecycle (`sessions/create`, `sessions/open`)
- Centralized test Domain Host helper on supervisor primitives

### Test-only

- `tests/helpers/domain-api.mjs` spawn wrappers
- `GET /v1/scenes/{id}/state` transitional HTTP alias
- Kernel `create_scene()` for Python unit tests

### Superseded

- Per-test duplicate `startDomainApi` + `/v1/scenes` readiness probes
- `POST /v1/scenes` HTTP route
- `createScene()` DSH client method
- Manual multi-console startup as intended product model

### Transitional

- `GET /v1/scenes/{id}/state` — remove when no consumer remains

---

## 14. Challenge / refinement

| Question | Verdict |
|----------|---------|
| One coherent production startup path? | **Yes** — `npm start` / `HolyGrailRuntimeSupervisor` |
| Supervision separate from RP logic? | **Yes** |
| Health gating replaces timing hacks? | **Yes** in supervisor + test helper |
| Startup failure without orphans? | **Yes** (health timeout + DSH bootstrap rollback) |
| Shutdown preserves persisted state? | **Yes** |
| Domain Host URL centralized? | **Yes** — `HG_DOMAIN_HOST_URL` |
| `/v1/scenes` left production? | **Yes** (POST removed; DSH migrated) |
| Python/DSH lifecycles too coupled? | **No** — attach mode + independent restart tests preserved |
| Windows practical? | **Yes** |
| UI integration straightforward? | **Yes** — ready contract exposed |

**Refinement applied:** Supervisor attach mode uses explicit `domainHostUrl` option only — does not read ambient `HG_DOMAIN_HOST_URL` (prevents stale-env skip-spawn bug).

---

## 15. Architecture verdict

**Validated with refinements**

The Node supervisor model is the correct production entrypoint. Health identity (`service` field) prevents false readiness on port collision. Test infrastructure consolidated without requiring full supervisor in every deterministic test.

---

## 16. Repository state

| Field | Value |
|-------|-------|
| Commit | `0703fe3` — `feat(v2): M6 supervised runtime startup` |
| Branch | `main` |
| `origin/main` | aligned after push |
| Working tree | clean |

---

## 17. Next recommended migration slice

**M7 — UI / launcher integration:** Wire a user-facing entrypoint (e.g. `Launch-Holy-Grail-V2.bat` or Streamlit shell) to `HolyGrailRuntimeSupervisor`, consume the ready contract, and surface runtime health — **do not implement without Governance review.**
