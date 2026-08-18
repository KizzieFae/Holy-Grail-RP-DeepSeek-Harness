# V2 HgRoundOrchestrator Promotion — M4 Implementation Report

**Status:** Completed (M4 — slim orchestrator promotion)  
**Date:** 2026-08-18  
**M3 HgTraceEmitter anchor:** `8a6aade`  
**Implementation HEAD:** _(set at commit)_

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `8a6aade` |
| Scope | M4 — promote `HgRoundOrchestrator`, remove `HolyGrailRpRuntime` |

Pre-slice validation: 37 Python + 30 Node tests green.

---

## 2. Pre-M4 responsibility inventory

| Responsibility | Classification |
|----------------|----------------|
| `runRound` lifecycle | **Permanent** — orchestrator |
| Eligibility/participation sequencing | **Permanent** |
| Phase delegation | **Permanent** |
| Round result assembly | **Permanent** |
| `runCharacterInference` | **Transitional** → phase executors |
| `mountStack` | **Transitional** → bootstrap `mountRpStack` |
| `syntheticDirectorDecision` | **Transitional** → `participationDirectorDecision` adapter |
| `eligibilityTrace` / `participationTrace` | **Permanent** — payload formatters in `round-helpers.mjs` |
| DSH stack composition | **Transitional** → `lib/mount-rp-stack.mjs` |

---

## 3. Standalone inference relocation

**From:** `HolyGrailRpRuntime.runCharacterInference()`  
**To:** `HgPhaseExecutors.runCharacterInference()` → `character-inference-slice.mjs`

Rationale: standalone character inference is phase execution (inference + validate + commit coordination), not round lifecycle.

Tests updated: `boundary-prototype`, `real-inference`, `provider-failure` call `phaseExecutors.runCharacterInference()`.

---

## 4. Composition/bootstrap decision

**Removed:** `mountStack` from orchestrator.

**Added:** `lib/mount-rp-stack.mjs` — `mountRpStack(ctx, config, options)` called from `bootstrap.mjs`.

Orchestrator consumes pre-registered services; bootstrap owns DSH/Cordis composition.

---

## 5. Synthetic Director decision

**Renamed:** `syntheticDirectorDecision` → `participationDirectorDecision` in `round-helpers.mjs`.

**Kept** as commit-API shape normalization for direct participation selection, tagged `source: 'participation_policy'`. Not a Director inference result — preserves trace semantics while unifying downstream character phase input.

---

## 6. HgRoundOrchestrator contract

**Cordis service:** `hgRoundOrchestrator` (`HgRoundOrchestrator`)

**Public API:**
- `runRound(options)` — sole production orchestration entry

**Depends on:** Domain API client, `ctx.hgPhaseExecutors`, `ctx.hgTraceEmitter`, `ctx.agentLoop` (scene session only).

**Does not expose:** inference mechanics, context bridge, provider config, standalone character inference.

---

## 7. Service dependency graph

```text
bootstrap / mountRpStack
  ├── HgContextBridge
  ├── HgTraceEmitter
  ├── HgPhaseExecutors
  │     ├── inference substrate
  │     │     └── HgContextBridge
  │     ├── director/character/narrator phases
  │     └── character-inference-slice
  ├── DSH agent loop + provider adapters
  └── HgRoundOrchestrator
        ├── Domain API client
        ├── HgPhaseExecutors (runDirector/runCharacter/runNarrator)
        └── HgTraceEmitter (round-level events)
```

---

## 8. Implemented cleanup

| Action | Detail |
|--------|--------|
| **Added** | `hg-round-orchestrator/`, `mount-rp-stack.mjs`, `character-inference-slice.mjs` |
| **Removed** | `hg-rp-runtime/` plugin directory entirely |
| **Renamed** | `HolyGrailRpRuntime` → `HgRoundOrchestrator`, `hgRpRuntime` → `hgRoundOrchestrator` |
| **Updated** | `bootstrap.mjs`, all Node tests, `cordis.yml` |

No compatibility alias retained.

---

## 9. State-authority proof

- Python `kernel.py`, `participation_policy.py` unchanged.
- Orchestrator calls Domain API only; no validation/commit semantics duplicated.
- Phase executors unchanged in authority boundaries.

---

## 10. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python | 37 passed |
| V2 Node | 30 passed |
| Live single inference | passed |
| Live full round | passed |

Zero intentional behavior change.

---

## 11. Clean-V2 review

| Component | Classification |
|-----------|----------------|
| `HgRoundOrchestrator` | **Permanent** |
| `HgPhaseExecutors` + slices | **Permanent** |
| `HgContextBridge`, `HgTraceEmitter`, inference substrate | **Permanent** |
| `HolyGrailRpRuntime`, `hg-rp-runtime/` | **Removed** |
| `mountStack` on orchestrator | **Removed** |
| HTTP Domain API, FixtureStore | Transitional |
| `participationDirectorDecision` | Permanent adapter (tagged) |
| `mount-rp-stack.mjs` | Permanent composition |

---

## 12. Simplification metrics

| Metric | Before M4 | After M4 |
|--------|-----------|----------|
| Orchestrator `service.mjs` LOC | 579 | **329** |
| `round-helpers.mjs` | (inline) | 53 |
| `runCharacterInference` on orchestrator | 187 LOC | **0** (moved to phase executors) |
| `mountStack` on orchestrator | 18 LOC | **0** (moved to bootstrap) |
| Deleted `hg-rp-runtime/` | 579+ LOC | **removed** |

Orchestrator now reads as round lifecycle + result assembly only.

---

## 13. Mature-architecture assessment (vs `8cd68d4`)

| Target from investigation | Status |
|---------------------------|--------|
| Thin `HgRoundOrchestrator` | **Achieved** (~329 LOC) |
| `HgPhaseExecutors` | **Achieved** |
| `HgContextBridge` | **Achieved** |
| `HgTraceEmitter` | **Achieved** |
| Python authoritative kernel | **Unchanged** |

**Next major work:** replace transitional boundaries (HTTP Domain API, FixtureStore), not further DSH decomposition.

HTTP Domain API is now the largest obvious migration scaffold. FixtureStore prevents real authoritative persistence until in-process or stable RPC + real store lands.

---

## 14. Challenge / refinement

| Question | Finding |
|----------|---------|
| Genuinely thin? | **Yes** — single `runRound` API |
| Lifecycle-only? | **Yes** |
| Standalone inference relocated? | **Yes** — phase executors |
| Bootstrap removed from wrong layer? | **Yes** |
| Synthetic Director cleaner? | **Yes** — renamed, documented |
| Migration names removed? | **Yes** — no `HolyGrailRpRuntime` |
| Python authoritative? | **Yes** |
| Closer to clean V2? | **Yes** |

---

## 15. Architecture verdict

**Validated as designed.**

---

## 16. Next recommended migration slice

**M5: In-process Domain API binding** — replace HTTP transport + FixtureStore with in-process Python domain kernel invocation (or stable RPC), enabling real authoritative persistence path.

Do not implement without Governance review.
