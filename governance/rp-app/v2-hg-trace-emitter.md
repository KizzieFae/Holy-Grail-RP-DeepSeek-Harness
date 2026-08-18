# V2 HgTraceEmitter Extraction — M3 Implementation Report

**Status:** Completed (M3 — trace emitter extraction)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**M1 HgContextBridge anchor:** `50715d1`  
**M2 HgPhaseExecutors anchor:** `4f3e135`  
**Implementation HEAD:** `380e333`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `4f3e135` |
| Assigned workflow weight | standard |
| Effective workflow weight | full |
| Scope | M3 — `HgTraceEmitter` extraction only |

Pre-slice validation: 37 Python + 28 Node tests green.

---

## 2. Previous trace architecture

| Producer | Mechanism |
|----------|-----------|
| `events.mjs` | `appendHgEvent(session, type, data)` + `baseCorrelation(fields)` |
| `HolyGrailRpRuntime` | Round-level events + `runCharacterInference` events via direct append |
| `director-phase.mjs` | 4 event types via `appendHgEvent` + spread `correlation()` |
| `character-phase.mjs` | 4 event types |
| `narrator-phase.mjs` | 3 event types |
| `HgPhaseExecutors` | `_correlation()` wrapper over `baseCorrelation` |

**15 production `hg/*` event emission sites** across orchestrator and phase modules.

---

## 3. HgTraceEmitter design

**Cordis service:** `hgTraceEmitter` (`HgTraceEmitter`)

**Registration:** `bootstrap.mjs` constructs before phase executors; `mountStack()` and `HgPhaseExecutors.ensure()` call `HgTraceEmitter.ensure()`.

**API:**

```text
correlation(scope) → { hg_scene_id, hg_round_id, dsh_scene_session_id }

emit(session, type, scope, payload)
  → session.append(type, { ...correlation(scope), ...payload })
```

**Lifecycle:** Stateless per emit; no domain state. Validates `type` against `HG_EVENT_TYPES` (15 types).

**Does not own:** domain decisions, validation, inference, retries, round sequencing.

---

## 4. Event/correlation model

**Centralized:**
- Scene/round/session correlation normalization (`scope` → snake_case fields)
- Session append mechanics
- Event type registry + validation

**Event-specific (callers):**
- Payload fields per semantic event (inference_id, manifest_id, proposed_move, domain_commit_id, etc.)
- When each event fires (phase/orchestrator lifecycle)

---

## 5. Implemented extraction

| File | Change |
|------|--------|
| `v2/rp_runtime/src/plugins/hg-trace-emitter/service.mjs` | **New** — sole HG event API |
| `v2/rp_runtime/src/plugins/hg-trace-emitter/index.mjs` | **New** |
| `v2/rp_runtime/src/plugins/hg-rp-runtime/events.mjs` | **Superseded** — re-exports `HG_EVENT_TYPES` only |
| Phase modules + orchestrator | Migrated to `trace.emit()` |
| `bootstrap.mjs`, `cordis.yml` | Register `HgTraceEmitter` |
| `tests/hg-trace-emitter.test.mjs` | **New** — correlation + type validation |

**Removed:** `appendHgEvent`, `baseCorrelation`, `_correlation` in orchestrator, `_correlation` in phase executors.

---

## 6. Evidence-separation proof

| Layer | Owner | M3 impact |
|-------|-------|-----------|
| **A. DSH native** | DSH session per inference | Unchanged; `inference_trace` on HG events remains compact summary |
| **B. HG execution events** | `HgTraceEmitter` | Sole emission path; correlates via IDs |
| **C. Domain truth** | Python kernel | Unchanged; `domain_commit_id` referenced, not created by emitter |

No full prompts, reasoning bodies, or DSH session duplication added.

---

## 7. Event-order / state-authority proof

| Invariant | Evidence |
|-----------|----------|
| `move-committed` before `narrator-started` | `narrator-round.test.mjs` passes |
| Proposed ≠ committed | `boundary-prototype.test.mjs`, `hg/move-proposed` vs `hg/move-committed` |
| `canon_preserved` on narrator failure | `narrator-round.test.mjs` |
| Participation/director ordering | `participation-round.test.mjs`, `director-character-round.test.mjs` |

Event payloads and ordering unchanged — only emission path moved.

---

## 8. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python | 37 passed |
| V2 Node (all) | **30 passed** (+2 new trace tests) |
| Live single inference | passed |
| Live full round | passed |

Zero intentional behavior change.

---

## 9. Clean-V2 cleanup

| Component | Classification |
|-----------|----------------|
| `HgTraceEmitter` | **Permanent** — sole `hg/*` emission path |
| `HG_EVENT_TYPES` | **Permanent** |
| `appendHgEvent`, `baseCorrelation` | **Removed** |
| Direct session append in phase/orchestrator | **Removed** |
| `events.mjs` | Transitional re-export shim (can delete when imports updated) |

---

## 10. Simplification metrics

| Metric | Before M3 | After M3 |
|--------|-----------|----------|
| `service.mjs` LOC | 612 | **579** |
| Phase executor LOC (3 modules) | 436 | **436** (net ~same; cleaner deps) |
| `hg-trace-emitter/service.mjs` LOC | — | **70** |
| Production emission paths | scattered | **1** |

**Orchestrator:** no `_correlation`, no `appendHgEvent`; uses `trace.emit()`.

**Phase executors:** `trace` dep replaces `correlation` + direct append.

---

## 11. Domain-audit implications

**Future cleanup candidates (not removed in M3):**
- `raw_model_output` on HG events — joinable from DSH inference sessions by `inference_id`
- `inference_trace` compact summaries — already reference DSH evidence; avoid expanding
- Python domain audit vs HG events — HG events are runtime correlation; Python stores authoritative commits

M3 clarifies: HG events = **correlation + decision evidence**, not a third copy of model I/O.

---

## 12. M4 readiness assessment

`HolyGrailRpRuntime` (579 LOC) still contains:

| Remaining responsibility | M4 target |
|--------------------------|-----------|
| `runRound` lifecycle loop | Keep — rename to `HgRoundOrchestrator` |
| `mountStack` / DSH composition | Keep or move to bootstrap factory |
| `runCharacterInference` standalone slice | Extract to phase executors or test harness |
| Trace projection helpers (`eligibilityTrace`, `participationTrace`) | Optional move to trace emitter or small lib |
| `syntheticDirectorDecision` | Keep until participation transport matures |
| Round result assembly | Keep in orchestrator |

**Recommended M4 slice:** Slim orchestrator rename + extract `runCharacterInference` into `HgPhaseExecutors.runCharacterInferenceSlice()` (or equivalent), reducing orchestrator to pure round lifecycle.

---

## 13. Challenge / refinement

| Question | Finding |
|----------|---------|
| One production path? | **Yes** — `HgTraceEmitter.emit` only |
| Meaningful boundary? | **Yes** — evidence-only, typed |
| Remained evidence-only? | **Yes** |
| Event semantics unchanged? | **Yes** — 30 tests |
| Became domain service? | **No** |
| Avoided DSH duplication? | **Yes** |
| Correlation more consistent? | **Yes** — single `scope` object |
| Phase executors cleaner? | **Yes** |
| M4 obvious? | **Yes** — orchestrator + standalone slice |
| Superseded clutter removed? | **Yes** |

---

## 14. Architecture verdict

**Validated as designed.**

---

## 15. Next recommended slice

**M4: Slim orchestrator to `HgRoundOrchestrator`** — extract `runCharacterInference` into phase executors; reduce `HolyGrailRpRuntime` to round lifecycle + result assembly only.

Do not implement without Governance review.
