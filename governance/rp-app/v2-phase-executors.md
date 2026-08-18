# V2 Phase Executor Extraction — M2 Implementation Report

**Status:** Completed (M2 — phase executor extraction)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Mature architecture anchor:** `8cd68d4`  
**M1 HgContextBridge anchor:** `50715d1`  
**Implementation HEAD:** _(set at commit)_

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `50715d1` |
| Assigned workflow weight | standard |
| Effective workflow weight | full |
| Scope | M2 — phase executor extraction |

Pre-slice validation: 37 Python + 28 Node tests green.

---

## 2. Previous orchestrator responsibilities

`HolyGrailRpRuntime` (`service.mjs`, 1110 LOC) previously owned:

| Category | Responsibilities |
|----------|------------------|
| **Lifecycle** | `runRound` loop, eligibility, participation, completion, result shaping |
| **Phase execution** | `_runDirectorPhase`, `_runCharacterTurn`, `_runNarratorPresentation` |
| **Shared inference** | `_runEphemeralInference` (agent, bridge, trace, cleanup) |
| **Standalone slice** | `runCharacterInference` (live provider test path) |
| **Stack mount** | DSH plugins, context bridge |

---

## 3. Phase-executor architecture

**Chosen:** Option A — one `HgPhaseExecutors` Cordis service with role-specific modules.

```text
HgPhaseExecutors (Cordis service: hgPhaseExecutors)
    runDirector()  → director-phase.mjs
    runCharacter() → character-phase.mjs
    runNarrator()  → narrator-phase.mjs
    runEphemeralInference() → inference-substrate.mjs
```

**Rationale:** Shared lifecycle, dependencies (`HgContextBridge`, inference config), and substrate; no independent per-role Cordis configuration; avoids micro-service fragmentation while enabling later split if needed.

---

## 4. Director executor

**Owns:** ephemeral Director inference, role profile, manifest via `HgContextBridge`, attempt loop, `hg/director-proposed|rejected|accepted|inference-failed` events, DSH trace extraction.

**Does not own:** eligibility, participation policy, Python `validateDirectorDecision` semantics.

---

## 5. Character executor

**Owns:** ephemeral Character inference, manifest registration, structured output capture, retry loop, move-proposed/rejected/committed events, inference-failed handling.

**Does not own:** validation rules or continuity commit semantics — coordinates `api.validateMove` / `api.commitMove` without reimplementing them.

---

## 6. Narrator executor

**Owns:** post-commit `prepareNarratorContext`, ephemeral inference, `hg/narrator-started|completed|failed`, presentation result shaping.

**Remains:** presentation-only, post-commit, `canon_preserved: true` on failure.

---

## 7. Shared inference substrate

`inference-substrate.mjs` — `createInferenceSubstrate(ctx, inferenceConfig)`:

- ephemeral agent creation
- mock adapter registration
- `HgContextBridge.registerManifest`
- DSH turn execution + `waitForIdle`
- `extractInferenceTrace`
- registration/adapter cleanup

Single production path used by all three phase executors and `runCharacterInference`.

---

## 8. Cordis boundary decision

**Option A chosen** — one `HgPhaseExecutors` service.

Not Option C (three services): no independent lifecycle or replaceable per-role wiring.  
Not Option B (separate inference service): substrate is internal module; exposing as second Cordis service adds registration overhead without benefit.

`HolyGrailRpRuntime` remains the round orchestrator; phase executors are execution delegates.

---

## 9. State-authority proof

- Python `kernel.py`, `participation_policy.py` unchanged.
- Phase executors call Domain API for `prepare*Context`, `validate*`, `commitMove` — no validation logic duplicated in TypeScript.
- Event payloads and API call shapes preserved verbatim from pre-M2 implementation.

---

## 10. Isolation / trace proof

| Concern | Evidence |
|---------|----------|
| Per-role ephemeral sessions | Unchanged — substrate creates `SessionId(hg-inf-*)` per inference |
| Context bridge scoping | Via M1 `HgContextBridge` on `agent.ctx` |
| Event ordering | All 28 Node tests pass including context-isolation, director/character/narrator rounds |
| Trace correlation | `role_inference_traces`, `inference_trace` on events unchanged |

Event emission remains in phase modules (M3 `HgTraceEmitter` deferred).

---

## 11. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python | 37 passed |
| V2 Node (all) | 28 passed |
| Live single inference | passed (with `DEEPSEEK_API_KEY`) |
| Live full round | passed (with `DEEPSEEK_API_KEY`) |

Zero intentional behavior change.

---

## 12. Clean-V2 cleanup

| Component | Classification |
|-----------|----------------|
| `HgPhaseExecutors` + modules | **Permanent** |
| `inference-substrate.mjs` | **Permanent** |
| `_runDirectorPhase`, `_runCharacterTurn`, `_runNarratorPresentation` | **Removed** from orchestrator |
| `_runEphemeralInference` | **Removed** from orchestrator |
| `HgContextBridge`, `InferenceProfile` | **Permanent** (unchanged) |
| HTTP Domain API, FixtureStore | Transitional |
| `runCharacterInference` | Transitional test/live slice on orchestrator (uses phase substrate) |

No duplicate phase execution paths retained.

---

## 13. Orchestrator simplification

| Metric | Before M2 | After M2 |
|--------|-----------|----------|
| `service.mjs` LOC | 1110 | 612 |
| Phase executor LOC | — | 594 (across 7 files) |

**Removed from orchestrator:** all role inference mechanics, ephemeral inference substrate.

**Retained:** round lifecycle, participation/director bypass policy, eligibility loop, completion classification, `runCharacterInference` standalone slice, stack mount.

Orchestrator now reads primarily as lifecycle coordination delegating `phaseExecutors.runDirector|runCharacter|runNarrator`.

Target ~200–400 LOC requires M3 (trace) + M4 (further slimming) — not in scope for M2.

---

## 14. Challenge / refinement

| Question | Finding |
|----------|---------|
| Orchestrator simpler? | **Yes** — 498 LOC removed (-45%) |
| Meaningful boundaries? | **Yes** — lifecycle vs execution vs substrate |
| Unnecessary fragmentation? | **No** — one service, modules not micro-plugins |
| Shared inference truly shared? | **Yes** — single substrate |
| Python authoritative? | **Yes** |
| Role isolation unchanged? | **Yes** |
| Trace semantics intact? | **Yes** |
| Hidden orchestration coupling? | `runCharacterInference` still on orchestrator — acceptable transitional slice |
| Narrator optional renderer? | **Yes** — isolated in `narrator-phase.mjs` |
| M3 easier? | **Yes** — events colocated in phase modules, ready to delegate to emitter |
| V2 clutter reduced? | **Yes** — superseded methods deleted |

---

## 15. Architecture verdict

**Validated as designed.**

---

## 16. Next recommended slice

**M3: Extract `HgTraceEmitter`** — centralize `appendHgEvent` + correlation patterns from phase modules and orchestrator. Do not implement without Governance review.
