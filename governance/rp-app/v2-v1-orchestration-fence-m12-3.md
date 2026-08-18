# V2 V1 Orchestration Fence — M12.3 Implementation Report

**Status:** Completed (M12.3 — physical legacy fence; no deletion)  
**Date:** 2026-08-18  
**M12.2 anchor:** `be96cf9`  
**Implementation HEAD:** `e0d5337`

---

## 1. Scope

Physically fence remaining V1 Streamlit/AutoGen/turn_runner orchestration into `legacy/v1_orchestration/` while keeping `v2/domain` as the single authoritative domain implementation.

---

## 2. Pre-fence rp_app inventory

| Category | Count | Examples |
|----------|-------|----------|
| Domain shims (M12.2) | 114 | `continuity_manager.py` → `v2/domain/modules/` |
| Substantive V1 runtime | 161 | `app.py`, `turn_runner*`, `model_client`, UI, prompts |
| Orchestration-local data | 1 tree | `rp_app/data/` (progression scenarios, rp_audits) |
| Character loader + AutoGen factory | 2 | `character_loader.py`, `v1_autogen_agents.py` |

---

## 3. Legacy fence architecture

**Location:** `legacy/v1_orchestration/` (Python package `legacy.v1_orchestration`)

**Import strategy (B + explicit package):**
- `legacy.v1_orchestration.bootstrap.ensure_v1_orchestration_paths()` registers:
  - `legacy/v1_orchestration/` (flat orchestration imports)
  - `autogen_rp/python/rp_app/` (domain shims only)
  - `v2/` + `v2/domain/modules/` (neutral domain)
- V1 pytest `conftest.py` calls bootstrap automatically
- V2 **never** calls legacy bootstrap

**Legacy smoke:** `python -m legacy.v1_orchestration --check-imports`

---

## 4. Components moved

- Streamlit entry: `app.py`, `ui_*`, `app_*` glue
- Orchestration: `turn_runner*`, `app_turn_director`, `orchestration_*`
- AutoGen: `model_client.py`, `semantic_validation.py`, agent wiring
- Prompt runtime: `prompt_*`, `app_turn_prompting`, retrieval assembly
- Headless: `headless_*`, simulation runners
- Character AutoGen: `character_loader.py`, `v1_autogen_agents.py`
- Local data/docs: `data/`, `ARCHITECTURE.md`, runtime README

---

## 5. Components intentionally not moved

| Item | Reason |
|------|--------|
| `v2/domain/modules/*` | Permanent neutral domain (M12.2) |
| `v2/domain/character_cards.py` | Permanent card I/O (M12.1) |
| `autogen_rp/python/rp_app` domain shims | Reverse-dependency bridge to `v2/domain` |
| `autogen_rp/python/data/` | Shared authored assets (characters, templates, sessions) |
| Vendored `autogen_rp/python/packages/` | Dependency vendor tree |

---

## 6. V2 dependency audit

| Check | Result |
|-------|--------|
| `v2/domain_api` → legacy | **0** |
| `v2/domain` → legacy | **0** |
| `v2/rp_runtime` → legacy | **0** |

Test: `v2/tests/test_legacy_fence_m12_3.py`

---

## 7. AutoGen containment audit

Production AutoGen imports confined to:
- `legacy/v1_orchestration/` (runtime)
- `autogen_rp/python/packages/` (vendor)
- `autogen_rp/python/validation_runs/` (evidence)
- Tests importing fenced runtime via bootstrap

**V2 / v2/domain:** **0** AutoGen imports

---

## 8. Streamlit boundary audit

| Area | Streamlit |
|------|-----------|
| `legacy/v1_orchestration/` | V1 runtime UI (fenced) |
| `v2/ui/streamlit_app.py` | V2 production shell (distinct) |
| `v2/domain*` | **0** |

---

## 9. Neutral-domain single-implementation proof

Substantive domain modules exist only under `v2/domain/modules/`. `rp_app` retains forwarding shims only (114). No duplicate continuity/validation/memory implementations in legacy tree.

---

## 10. V1 compatibility strategy

- Pytest `conftest.py` bootstraps legacy paths globally
- Flat import names preserved (`turn_runner`, `model_client`, `character_loader`)
- Individual tests may still `sys.path.insert(rp_app)` — conftest runs first

---

## 11. Compatibility shims

| Shim location | Purpose | Removal (M12.4) |
|---------------|---------|-------------------|
| `autogen_rp/python/rp_app/*.py` (114) | Domain forward to `v2/domain/modules` | Delete when V1 tests migrate to `domain.bootstrap` |
| `rp_app/__init__.py` | Deprecation notice | With shim tree |

No second shim layer in legacy.

---

## 12. Documentation/startup cleanup

- `autogen_rp/python/rp_app/DEPRECATED.md` — V2-first launch guidance
- `legacy/v1_orchestration/README.md` — moved from rp_app
- Production entry unchanged: `Launch-Holy-Grail-V2.bat`

---

## 13. Repository layout after fence

```text
v2/
  domain/           # permanent neutral semantics
  domain_api/       # Domain Host
  rp_runtime/       # Node orchestration
  ui/               # V2 Streamlit shell
legacy/
  v1_orchestration/ # fenced V1 runtime (161 modules)
autogen_rp/python/
  rp_app/           # domain shims only (~109 .py)
  data/             # shared authored assets
  tests/            # V1 evidence suite
  packages/         # vendored AutoGen
```

---

## 14–15. Validation

```text
python -m pytest v2/tests/ -q                         → 110 passed
cd v2/rp_runtime && npm test                          → 51 passed
python -m legacy.v1_orchestration --check-imports     → legacy-v1-import-ok
V1 targeted (loader, continuity, grounding, turn_runner*) → 92 passed
known: test_descriptive_exit_updates_authoritative_presence_state → 1 failed (pre-existing)
```

---

## 16. Legacy launch smoke

`python -m legacy.v1_orchestration --check-imports` imports `turn_runner`, `model_client`, `CharacterLoader` successfully.

---

## 17. M12.4 deletion-candidate inventory

| Component | M12.4 action |
|-----------|--------------|
| `legacy/v1_orchestration/` entire tree | **Delete** when product gaps closed + CI migrated |
| `autogen_rp/python/rp_app` shims | **Delete** after V1 test import migration |
| `autogen_rp/python/packages/autogen*` | **Delete** when no test/validation depends |
| V1 pytest suite (orchestration-only) | **Archive or trim** |
| `validation_runs/` | **Retain as evidence** until governance review |

**Retain until product gap closes:**
- V2 opening/bootstrap parity (does not require keeping turn_runner)
- Player/settings UX (does not require keeping turn_runner)

---

## 18. Reassessed blockers

Product capability gaps are **not** runtime-retention requirements. Missing V2 opening UI justifies future V2 work — not indefinite `turn_runner` preservation.

---

## 19. AutoGen removal readiness

| Gate | Status |
|------|--------|
| Imports outside legacy/vendor/tests | **Clear** |
| V2 independence | **Yes** |
| Remaining AutoGen consumers | `legacy/v1_orchestration/*`, validation_runs, vendored packages |
| V1 tests depending on AutoGen | Orchestration/agent tests via bootstrap |

---

## 20. Architecture verdict

**Validated as designed**

---

## 21. Next recommended slice

**M12.4 — Legacy orchestration deletion** after governance review of product-gap checklist and V1 test migration plan.
