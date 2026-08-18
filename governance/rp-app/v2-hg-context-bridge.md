# V2 HgContextBridge Extraction — M1 Implementation Report

**Status:** Completed (M1 — context bridge extraction)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Mature plugin architecture anchor:** `8cd68d4`  
**Implementation HEAD:** `b1bc4ef`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `8cd68d4` |
| Assigned workflow weight | standard |
| Effective workflow weight | full |
| Bootstrap profile | full V2 implementation |
| Scope | M1 — `HgContextBridge` extraction only |

Pre-slice validation: 37 Python + 26 Node tests green (24 deterministic + 2 live with key).

---

## 2. Previous context path

Manifest → DSH registration lived in:

| Location | Responsibility |
|----------|----------------|
| `v2/rp_runtime/src/lib/inference-utils.mjs` | `registerManifestContributions()` — iterate contributions, call `agent.ctx.systemPrompt.context()`, return disposer |
| `HolyGrailRpRuntime._runEphemeralInference()` | Call registration, extract contribution IDs for trace, dispose after inference |

No other production callers. Python `kernel.prepare_*_context()` remained authoritative for content, ordering, and visibility.

---

## 3. HgContextBridge design

**Cordis service:** `hgContextBridge` (`HgContextBridge`)

**Registration:** `bootstrap.mjs` constructs `HgContextBridge` before `HolyGrailRpRuntime`; `mountStack()` ensures bridge exists if missing.

**API:**

```text
registerManifest({ agent, manifest })
  → {
      dispose(),
      manifestId,
      contributionIds,
      correlation: {
        manifest_id, inference_id, role, character_id,
        hg_scene_id, hg_round_id, turn_index, attempt_index,
        contribution_ids
      }
    }
```

**Lifecycle:** Per-inference registration on `agent.ctx`; `dispose()` unregisters all contributions when inference completes.

**Does not own:** context selection, perception, identity, retrieval, memory, token policy, domain authority, orchestration, provider config, validation, retries.

---

## 4. Implemented extraction

| File | Change |
|------|--------|
| `v2/rp_runtime/src/plugins/hg-context-bridge/service.mjs` | **New** — permanent bridge service |
| `v2/rp_runtime/src/plugins/hg-context-bridge/index.mjs` | **New** — export |
| `v2/rp_runtime/src/bootstrap.mjs` | Register bridge; export `HgContextBridge` |
| `v2/rp_runtime/src/plugins/hg-rp-runtime/service.mjs` | Delegate to `ctx.hgContextBridge`; remove inline registration |
| `v2/rp_runtime/src/lib/inference-utils.mjs` | **Removed** `registerManifestContributions` |
| `v2/rp_runtime/tests/hg-context-bridge.test.mjs` | **New** — trace correlation + scoped isolation |

---

## 5. Context ownership proof

- Python `DomainKernel.prepare_*_context()` unchanged — still decides contributions, `source_kind`, `authority_class`, `priority`, `content`, `provenance`.
- Bridge maps `contribution_id` → DSH `name`, `priority` → `order`, `content` → `text` without semantic reinterpretation.
- No Python context policy moved to TypeScript.

---

## 6. Isolation proof

| Test | Evidence |
|------|----------|
| `context-isolation.test.mjs` | Director/character/narrator manifests exclude wrong source kinds (Python) |
| `hg-context-bridge.test.mjs` | Disjoint contribution IDs across two agents; director trace excludes `character-private` IDs |
| `context-isolation.test.mjs` (session) | Distinct DSH inference session IDs per phase |

Registrations use `agent.ctx.systemPrompt.context()` — scoped to ephemeral inference agent, not global `ctx`.

---

## 7. Provenance / traceability proof

```text
PromptContributionManifest (Python)
        ↓
HgContextBridge.registerManifest()
        ↓
agent.ctx.systemPrompt.context({ name: contribution_id, order, text })
        ↓
DSH inference session events
        ↓
extractInferenceTrace({ manifestId, contributionIds })
```

`correlation` object on registration handle carries manifest/inference/role/scene IDs for join without duplicating prompt bodies in HG audit.

---

## 8. Behavioral validation

| Suite | Result |
|-------|--------|
| V2 Python (`pytest tests`) | 37 passed |
| V2 Node deterministic | 26 passed |
| `hg-context-bridge.test.mjs` | 2 passed |
| `real-inference.test.mjs` | passed (with `DEEPSEEK_API_KEY`) |
| `real-full-round.test.mjs` | passed (with `DEEPSEEK_API_KEY`) |

**Total Node:** 28 passed.

No intentional RP behavior change observed.

---

## 9. Clean-V2 cleanup

| Component | Classification |
|-----------|----------------|
| `HgContextBridge` | **Permanent** — sole manifest → DSH path |
| `PromptContributionManifest` / Python assembly | **Permanent** |
| `registerManifestContributions` | **Superseded — removed** |
| Inline registration in `HolyGrailRpRuntime` | **Superseded — removed** |
| HTTP Domain API, FixtureStore | Transitional (unchanged) |
| `HgMockLlmAdapter` | Test-only (unchanged) |

---

## 10. Orchestrator simplification

| Metric | Before | After |
|--------|--------|-------|
| `service.mjs` LOC | 1106 | 1110 |
| `inference-utils.mjs` LOC | 54 | 41 |
| `hg-context-bridge/service.mjs` LOC | — | 65 |

**Responsibilities removed from orchestrator:**
- `systemPrompt.context()` registration mechanics
- Contribution ID collection from manifest

**Responsibilities retained in orchestrator:**
- Phase sequencing, Domain API calls, inference execution, trace emission, dispose delegation

LOC net unchanged in orchestrator (mountStack guard + import offset extraction). **Semantic simplification:** orchestrator no longer knows DSH context registration mechanics — only calls `hgContextBridge.registerManifest()`.

M2 phase-executor extraction is cleaner: context transport is already a separate service.

---

## 11. Challenge / refinement

| Question | Finding |
|----------|---------|
| One production path? | **Yes** — only `HgContextBridge.registerManifest` |
| Stable boundary? | **Yes** — narrow transport; future contributors need no bridge changes |
| Semantics moved out of Python? | **No** |
| Per-inference isolation? | **Yes** — `agent.ctx` scoped |
| Provenance preserved? | **Yes** — contribution IDs + correlation object |
| Service too thin? | **No** — centralizes the only cross-runtime context transport; prevents re-scattering |
| Unrelated responsibilities? | **No** |
| Future DB/vector/memory? | **Compatible** — Python assembly unchanged; bridge unchanged |
| M2 simpler? | **Yes** |

---

## 12. Architecture verdict

**Validated as designed.**

`HgContextBridge` is justified permanent infrastructure — not a micro-plugin, not optional, not a model tool.

---

## 13. Next recommended slice

**M2: Extract phase executors** (Director / Character / Narrator) from `HolyGrailRpRuntime` into dedicated modules/services. Do not implement without Governance review.
