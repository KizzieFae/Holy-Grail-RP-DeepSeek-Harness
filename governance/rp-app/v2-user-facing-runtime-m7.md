# V2 User-Facing Runtime + UI/Launcher Integration — M7 Implementation Report

**Status:** Completed (M7 — first user-facing V2 application path)  
**Date:** 2026-08-18  
**M6 supervised-runtime anchor:** `1116881`  
**Implementation HEAD:** (see §19 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `1116881` |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |

Pre-slice: 45 Python + 40 Node tests green.

---

## 2. M7 surface strategy

**Decision: Option B — minimal new V2 Streamlit shell** + **Node application client/API layer**.

**Rejected for M7:**
- **Option A** (refactor V1 Streamlit) — imports `ContinuityManager`, AutoGen agents, and `st.session_state` authority coupling.
- **Option C** (CLI-only) — insufficient for session UX validation; CLI path exists via HTTP API but Streamlit provides the user-facing proof.

**Architecture:**

```text
Launch-Holy-Grail-V2.bat / npm run app
    ↓
bin/hg-app.mjs
    ├── HolyGrailRuntimeSupervisor (Domain Host + DSH)
    ├── HolyGrailApplicationClient
    ├── HTTP application API (localhost)
    └── Streamlit subprocess (presentation consumer)
```

Streamlit does **not** spawn Domain Host or construct provider clients.

---

## 3. Surface/runtime boundary

| Layer | Responsibility |
|-------|----------------|
| `v2/ui/streamlit_app.py` | Presentation only — HTTP calls to application API |
| `HolyGrailApplicationClient` | Session tracking, user-turn ingress, transcript cache, error classification |
| `createHolyGrailAppServer` | Thin REST surface for UI/tools |
| `HolyGrailRuntimeSupervisor` | Process lifecycle (unchanged from M6) |
| `HgRoundOrchestrator` | Round semantics (unchanged) |
| `domain-api-client` | Internal HTTP boundary (not exposed to UI) |

### Application API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Runtime + application status |
| `GET /api/status` | Health + active session + transcript |
| `POST /api/sessions/create` | `sessions/create` |
| `POST /api/sessions/open` | `sessions/open` |
| `GET /api/sessions/{id}/state` | Domain session snapshot |
| `GET /api/transcript` | Presentation transcript |
| `POST /api/turns/submit` | User turn → `runRound()` |

---

## 4. User-turn ingress

```text
userMessage
    ↓
detectForcedSpeaker()  [request boundary]
    ↓
application transcript (presentation cache)
    ↓
orchestrator.runRound({
  session: { mode: 'open', hg_session_id },
  forcedDesignation,
  inference options
})
    ↓
durable commit + narrator presentation
    ↓
transcript append + API response
```

No Domain Host user-message persistence seam added in M7 — user text is recorded in the **application presentation transcript**; authoritative RP state remains in Domain Host continuity via commits.

---

## 5. Session lifecycle UX

Streamlit sidebar:
- **Create session** — cast input → `POST /api/sessions/create`
- **Open session** — `hg_session_id` text field → `POST /api/sessions/open`
- **Session state** — turn counter, cast, location from Domain Host

No local synthetic scene state. Durable identity is `hg_session_id`.

---

## 6. Supervisor/application lifecycle

`bin/hg-app.mjs`:
1. `HolyGrailApplicationClient.start()` → supervisor → health → DSH ready
2. Application HTTP server on dynamic localhost port
3. Spawn Streamlit with `HG_APP_API_URL` (skip with `HG_SKIP_STREAMLIT=1`)
4. SIGINT/SIGTERM → stop Streamlit → close API → `supervisor.stop()`

---

## 7. User-facing entrypoint

| Entry | Command |
|-------|---------|
| Primary | `cd v2/rp_runtime && npm run app` |
| Windows wrapper | `Launch-Holy-Grail-V2.bat` (repo root, relative paths only) |
| Runtime only (M6) | `npm start` |
| API-only | `HG_SKIP_STREAMLIT=1 npm run app` |

---

## 8. Health/error behavior

Application status values: `idle`, `starting`, `ready`, `round_in_progress`, `failed`, `stopped`, `error`.

Failure categories surfaced to API consumers:
- `runtime_unavailable`
- `provider_failure`
- `domain_failure`
- `round_failure`

Streamlit displays runtime status and turn errors without exposing internal stack traces by default.

---

## 9. Transcript/presentation ownership

| Source | Role |
|--------|------|
| Application `transcript[]` | **User-facing presentation cache** for current app session |
| `round.presentation_text` | Authoritative narrator output per turn (from domain commit path) |
| Domain `SessionRepository` | Authoritative continuity, turn counter, committed moves |
| DSH inference sessions | Execution evidence only |

On session **open/resume**, transcript resets in the UI; domain state (turn counter, commits) loads from Domain Host. Full historical transcript projection from continuity is deferred.

---

## 10. Forced-speaker ingress

Implemented at application boundary: `detect-forced-speaker.mjs` (ported V1 intent).

Maps user text → `forcedDesignation` → `ParticipationDecision` (existing M4/M5 path).

No `pending_forced_speaker` Streamlit session flags.

---

## 11. V1 UI assessment

### Reused (presentation patterns only)
- Chat-style message display concept
- Cast comma-separated input
- Session resume by id

### Rejected (V1 authority coupling)
- `ContinuityManager` in `st.session_state`
- AutoGen `AssistantAgent` / `model_client` from UI
- `turn_runner` / `process_user_message` orchestration
- V1 `SessionManager` JSON as UI authority
- `pending_forced_speaker` session flags

---

## 12. `/v1/scenes` alias retirement

`GET /v1/scenes/{id}/state` **removed** — no remaining code consumers after M6/M7 migration.

---

## 13. Validation

| Suite | Result |
|-------|--------|
| Python `pytest` | **45 passed** |
| Node `npm test` | **46 passed** (+ application client/server/forced-speaker/live) |
| `hg-app` smoke (Windows, API-only) | **passed** |
| Application restart/resume test | **passed** |
| Live DeepSeek user turn | **passed** (when `DEEPSEEK_API_KEY` set) |

---

## 14. Clean-V2 review

### Permanent
- `HolyGrailApplicationClient`
- `createHolyGrailAppServer`
- `bin/hg-app.mjs`, `npm run app`
- `v2/ui/streamlit_app.py`
- `Launch-Holy-Grail-V2.bat`
- `detect-forced-speaker.mjs`

### Reused/refactored
- V1 forced-speaker heuristic (logic only, not session flags)
- Streamlit chat presentation pattern (new minimal shell)

### Superseded for V2 production path
- V1 Streamlit as production entrypoint
- UI-owned runtime authority
- `GET /v1/scenes/{id}/state` HTTP alias

### Transitional
- Application presentation transcript (not yet rebuilt from domain on resume)
- V1 `autogen_rp/python/rp_app/` (unchanged, not production V2 path)

---

## 15. V1 retirement candidates (Governance review required)

- `autogen_rp/python/rp_app/app.py` production entrypoint
- V1 `turn_runner` orchestration path once V2 UI covers required UX
- V1 `model_client` / AutoGen agent construction from UI bootstrap
- `pending_forced_speaker` session-state flags
- V1 `SessionManager` as UI authority (keep for V1 until explicit deletion slice)

---

## 16. Challenge / refinement

| Question | Verdict |
|----------|---------|
| UI is consumer not authority? | **Yes** |
| Valuable V1 UI without V1 runtime? | **Yes** — presentation patterns only |
| One clean user-turn ingress? | **Yes** — `submitUserTurn` |
| Durable sessions owned by Domain Host? | **Yes** |
| Supervision centralized? | **Yes** — `hg-app` owns all processes |
| Provider config outside UI? | **Yes** — `InferenceProfile` via runtime |
| Transcript coherent? | **Yes** with resume caveat documented |
| Forced-speaker clean? | **Yes** |
| Scene alias retired? | **Yes** |
| One-product launch? | **Yes** — `npm run app` / `.bat` |
| Repository more V2-like? | **Yes** |

---

## 17. Architecture verdict

**Validated with refinements**

Refinements: application presentation transcript is session-scoped in the UI layer; full resume transcript projection from domain continuity deferred.

---

## 18. Next recommended migration slice

**M8 — Domain transcript projection + V1 surface deprecation plan:** Project durable RP presentation history from Domain Host continuity into the application API on session open, then mark V1 Streamlit entrypoint deprecated with explicit removal conditions. **Do not implement without Governance review.**

---

## 19. Repository state

(Updated after commit/push)
