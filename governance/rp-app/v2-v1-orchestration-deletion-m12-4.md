# V2 V1 Orchestration Deletion — M12.4

**Status:** Complete  
**Date:** 2026-08-18  
**M12.3 validation anchor:** `1c9e499`  
**M12.4 completion HEAD:** (see §25 after commit)

**Governing principle:** Retire obsolete mechanisms, not valuable domain semantics.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-deletion HEAD | `1c9e499` (M12.3 validation) |
| `origin/main` | aligned at activation |
| Workflow | assigned standard / effective **full** |
| Bootstrap profile | full V2 implementation |
| Working tree | clean at activation |

---

## 2. M12.3 fenced-runtime inventory (pre-deletion)

| Component | Files (approx.) | Role |
|-----------|-----------------|------|
| `legacy/v1_orchestration/` | 418 files (166 `.py`) | Fenced V1 Streamlit + AutoGen orchestration |
| `autogen_rp/python/rp_app/` shims | 113 `.py` + `memory_layer/` | Domain import shims → `v2/domain/modules/` |
| V1 test suite | 154 test modules | Mixed domain + orchestration contracts |
| Evidence data | `rp_audits/`, progression scenarios | Audit replay + simulation fixtures |

---

## 3. Final deletion classification

### A — Superseded runtime (deleted)

- `turn_runner*` orchestration spine
- Streamlit `app.py` production entry and UI-owned runtime
- V1 Director/actor-selection AutoGen execution (`app_turn_director`, `model_client`, agent factories)
- V1 prompt-orchestration runtime (`app_turn_prompting`, `prompt_topology_issue240`, `semantic_validation` LLM paths)
- Headless simulation runtime (`headless_scene_simulation`, `headless_turn_runner_wire`)
- Legacy bootstrap (`legacy.v1_orchestration.bootstrap`)
- All `rp_app` domain shims (replaced by `domain.bootstrap.ensure_domain_paths()`)

### B — Product capability (spec retained, runtime deleted)

| Capability | Runtime deleted | Specification preserved |
|------------|-------------------|----------------------|
| Generated/full opening bootstrap | `bootstrap_composition`, `scene_start_bootstrap` | M12 investigation §product gaps |
| Player/settings UX | Streamlit sidebar modules | PRD + governance |
| Narrator semantic re-render | `turn_runner_character_render` semantic retry | V2 single-pass narrator phase |
| Retrieval-index selection | `prompt_retrieval_assembly`, episodic select runtime | `CANONICAL_KNOWLEDGE_MODEL.md`, scenario framework |
| Audit/debug UX | `audit_logger`, user callout review CLI | `governance/archive/v1-runtime/AUDIT_DOCUMENTATION.md` |

### C — Extract-first blockers

None encountered. Permanent domain semantics were already in `v2/domain/modules/` from M12.2.

### D — Test/evidence (retained/archived)

- `governance/archive/v1-runtime/` — ARCHITECTURE.md, AUDIT_DOCUMENTATION.md, README.md
- `autogen_rp/python/data/rp_audits/` — audit JSON fixtures (from legacy data)
- `v2/tests/test_presence_descriptive_exit_regression.py` — known presence discrepancy (`xfail`)

### E — Vendor/dependency (deferred M12.5)

- `autogen_rp/python/packages/*` vendored AutoGen packages unchanged

### F — Compatibility shims (deleted)

- 113 `rp_app/*.py` domain shims → **0**
- `rp_app/memory_layer/` broken shim → deleted (domain package at `v2/domain/modules/memory_layer/`)
- `legacy.v1_orchestration.bootstrap` → deleted with tree

**Residual shims: 0**

---

## 4. Superseded orchestration removed

Entire `legacy/v1_orchestration/` tree deleted including:

- `turn_runner.py`, `turn_runner_*`
- `app.py`, `app_message_processing.py`, `app_bootstrap.py`
- `model_client.py`, `v1_autogen_agents.py`, `character_loader.py`
- `app_turn_director.py`, `app_turn_rendering.py`, `app_turn_prompting.py`
- `headless_scene_simulation.py`, `headless_turn_runner_wire.py`
- `semantic_validation.py`, `orchestration_helpers.py`
- All Streamlit UI runtime modules

---

## 5. V1 UI/runtime entrypoint removal

- No runnable V1 Streamlit product path remains
- `autogen_rp/python/rp_app/` contains only `__init__.py` + `DEPRECATED.md`
- Production entry: `Launch-Holy-Grail-V2.bat` → `v2/rp_runtime/npm run app`

---

## 6. AutoGen runtime removal

- No production Holy Grail code imports AutoGen agent orchestration
- `v1_autogen_agents.py`, `model_client.py`, team recreation deleted
- Vendored packages remain for M12.5 assessment

---

## 7. V1 prompt-orchestration removal

Deleted runtime prompt builders tied to V1 turn loop. Neutral formatters retained in `v2/domain/modules/` (`prompt_builders.py`, `continuity_context_projector` consumers, etc.).

---

## 8. Compatibility-shim cleanup

| Shim | Consumers before | Action |
|------|------------------|--------|
| `rp_app/*.py` domain shims | V1 tests | Deleted; tests use `domain.bootstrap` |
| `legacy.v1_orchestration.bootstrap` | conftest, scripts | Deleted |
| `rp_app/memory_layer/__init__.py` | memory tests | Deleted; use domain `memory_layer` package |

**Residual orchestration compatibility shims: 0**

---

## 9. Test retirement/porting

| Category | Count | Action |
|----------|-------|--------|
| Orchestration-only tests (turn_runner, app, model_client, headless) | ~59 | Deleted with mechanism |
| Tests importing orchestration-only modules (audit UI, progression runtime, retrieval runtime) | ~58 | Deleted |
| Audit/callout tooling tests | 3 | Deleted (`user_callouts`, `user_callout_review`, `i251_replay`) |
| Domain contract tests | 358 | **Retained** — pass via `domain.bootstrap` |
| Presence regression | 1 | **Ported** to `v2/tests/test_presence_descriptive_exit_regression.py` (`xfail`) |
| V2 proof tests | +1 | `test_m12_4_orchestration_deletion.py` replaces M12.3 fence tests |

**Pre-M12.4 V1 baseline:** 1374 passed, 1 failed, 2 skipped  
**Post-M12.4 domain suite:** 358 passed  
**Post-M12.4 V2 suite:** 112 passed, 1 xfailed; Node 51 passed

---

## 10. Known descriptive-exit regression preservation

`test_descriptive_exit_updates_authoritative_presence_state` preserved at `v2/tests/test_presence_descriptive_exit_regression.py` with `@pytest.mark.xfail(strict=True)`. Behavior not fixed in M12.4.

---

## 11. Product-gap specification retention

Specifications retained in governance/PRD/scenario docs — not in deleted runtime code. See §3B.

---

## 12. Documentation/launcher cleanup

- `MODULE_INDEX.md` — M12.4 banner, historical disclaimer
- `ARCHITECTURE_OVERVIEW.md` — V2-first execution layer
- `autogen_rp/python/rp_app/DEPRECATED.md` — updated retirement state
- `Launch-Holy-Grail-V2.bat` — unchanged (sole launcher)
- Historical governance records unchanged (past tense accurate)

---

## 13. Dependency audit (post-deletion)

| Check | Result |
|-------|--------|
| V2 production imports from `legacy` | **0** |
| `v2/domain` imports from `legacy` | **0** |
| Production `turn_runner` references | **0** (tests/docs excluded) |
| Production AutoGen orchestration imports | **0** |
| V1 production entrypoints | **0** |
| `rp_app` runtime namespace | Empty shell only |

---

## 14. AutoGen dependency assessment

**Still present (M12.5 candidates):**

- `autogen_rp/python/packages/autogen-*` vendored source
- `autogen_rp/python/samples/` sample apps
- Package dependency declarations in vendored pyproject files

**Not present:**

- Production runtime imports of `autogen_agentchat`, `autogen_ext`, etc.

**Recommendation:** M12.5 — vendored AutoGen package removal after confirming no scripts/tests require live AutoGen.

---

## 15. autogen_rp residual assessment

| Category | Remains |
|----------|---------|
| Domain residue | **None** (in `v2/domain`) |
| Tests | `autogen_rp/python/tests/` — 35 domain modules |
| Data/assets | `autogen_rp/python/data/` — characters, templates, sessions, audits |
| Vendor | `autogen_rp/python/packages/` — AutoGen |
| Historical evidence | `validation_runs/`, archived docs |
| Scripts | Issue investigation scripts (non-production) |
| `rp_app/` | Deprecated empty namespace |

**Eventual moves:** data → top-level `data/`; vendor → `vendor/` or remove; tests → `tests/domain/` (future hygiene, not M12.4).

---

## 16. V2 production smoke

Validated via `npm test` in `v2/rp_runtime` (51 tests), including:

- Supervisor health-gated Domain Host startup
- DSH runtime after Domain Host healthy
- Full round through SessionRepository
- Application client session create + turn submit

Path confirmed: `Launch-Holy-Grail-V2.bat` → supervisor → Domain Host → DSH.

---

## 17. Behavioral validation

| Command | Result |
|---------|--------|
| `python -m pytest v2/tests/ -q` | **112 passed, 1 xfailed** |
| `cd v2/rp_runtime && npm test` | **51 passed** |
| `python -m pytest autogen_rp/python/tests/ -q` | **358 passed** |

---

## 18. Repository hygiene

- Removed empty `legacy/v1_orchestration/`
- Removed broken `rp_app/memory_layer/` shim
- Fixed `python.rp_app` import fallbacks in domain classifier modules
- Deleted obsolete `user_callout_review.py` script
- No intentional unrelated churn

---

## 19. Retirement metrics

| Metric | Before | After |
|--------|--------|-------|
| `legacy/v1_orchestration` files | 418 | **0** |
| `rp_app` substantive `.py` modules | 113 | **0** |
| LOC removed (diff stat) | — | **~74,343** |
| Compatibility shims | 113+ | **0** |
| V1 orchestration tests | ~117 | **0** |
| Surviving domain tests | — | **358** |
| V2→legacy production imports | 0 | **0** |

---

## 20. Remaining product-gap assessment

| Gap | Classification |
|-----|----------------|
| Opening/bootstrap | Required before V2 product completion |
| Player/settings UX | Required before V2 product completion |
| Narrator semantic retry | Optional enhancement (V2 single-pass accepted) |
| Retrieval index | Required before V2 product completion |
| Audit/debug UI | Optional enhancement (ops tooling) |

---

## 21. M12 orchestration-retirement status

**Is the parallel V1 orchestration runtime gone?** **Yes.**

**Does any remaining V1 code execute as part of the Holy Grail production RP path?** **No.** Production is exclusively V2 Domain Host + DSH runtime.

---

## 22. Clean-V2 classification

| Tier | Contents |
|------|----------|
| **Permanent production** | `v2/domain`, `v2/domain_api`, `v2/rp_runtime`, `v2/ui` |
| **Remaining legacy** | None (orchestration deleted) |
| **Transitional** | `autogen_rp/python/data/`, domain tests under `autogen_rp/python/tests/` |
| **Evidence/archive** | `governance/archive/v1-runtime/`, `validation_runs/` |
| **Vendor/dependency** | `autogen_rp/python/packages/` (M12.5) |

---

## 23. Challenge/refinement

- Deleted only mechanisms with validated V2 replacements ✓
- Domain semantics preserved in `v2/domain/modules/` ✓
- Product gaps documented without retaining runtime ✓
- No V2 legacy imports ✓
- AutoGen absent from production orchestration ✓
- No runnable competing V1 product ✓
- Obsolete implementation tests removed; domain contracts retained ✓
- Active docs updated to V2-first ✓

---

## 24. Architecture verdict

**Validated as designed** — parallel V1 orchestration runtime removed; V2 production path intact; domain library unaffected.

---

## 25. Repository state

Recorded at commit time (see git log after push).

---

## 26. Next recommended migration slice

**M12.5 — Vendored AutoGen package removal:** Remove `autogen_rp/python/packages/autogen-*` and dependency declarations after confirming no remaining test/script imports require live AutoGen. Do not implement without Governance review.
