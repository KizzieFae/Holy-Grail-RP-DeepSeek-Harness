# V2 Domain Library — M12.2 Implementation Report

**Status:** Completed (M12.2 — framework-neutral domain library extraction)  
**Date:** 2026-08-18  
**M12.1 anchor:** `e89508d`  
**Implementation HEAD:** (see §25 after commit)

---

## 1. Scope

Extract the V2 transitive dependency closure (~113 modules) from `autogen_rp/python/rp_app/` into permanent `v2/domain/modules/`, eliminating V2 production imports through legacy path hacks.

---

## 2. Pre-M12.2 V2 → rp_app inventory

| V2 consumer | Legacy imports |
|-------------|----------------|
| `session_state`, `session_setup`, `session_repository` | `ContinuityManager`, `CharacterState`, `SessionManager`, setup seam, scene templates |
| `kernel` | validation, perception, narrator formatter, issue240 |
| `memory_write_policy`, `memory_retrieval` | memory_layer, perception, character state |
| `continuity_context_projector` | scene_grounding |
| `authored_knowledge` | canonical_compile_adapters |
| `knowledge_write_policy` | continuity_state_canon, continuity_canon_anchors |
| `setup_catalog` | scene_opener, scene_template |

All used `_RP_APP` `sys.path.insert` into `autogen_rp/python/rp_app`.

---

## 3. Module classification

| Class | Modules | Action |
|-------|---------|--------|
| A — Pure domain | continuity*, validation*, perception*, memory_layer, scene_grounding, scene_template*, canonical_compile*, issue240 | Moved to `v2/domain/modules/` |
| C — Persistence | `session_manager`, `cross_session_memory_policy` | Moved (Option A) |
| D — Formatter | `prompt_builders` (narrator render only used by V2) | Moved |
| Legacy-only | `character_loader` shim | Unchanged — V1 AutoGen compat |
| F — Uncertain | `progression_simulation_scenarios` | In closure via validation; moved with validation tree |

No moved module imports AutoGen, Streamlit, `model_client`, or `turn_runner`.

---

## 4. Final neutral domain package structure

```text
v2/domain/
  bootstrap.py          # ensure_domain_paths()
  paths.py              # repo data-dir helpers
  character_cards.py    # M12.1 card I/O
  modules/              # flat namespace (109 modules + memory_layer/)
    continuity_manager.py
    response_validation*.py
    perception_audibility*.py
    memory_layer/
    session_manager.py
    scene_*.py
    ...
```

Subpackage grouping is conceptual; runtime uses flat imports via `modules/` on `sys.path`.

---

## 5–10. Extracted layers

| Layer | Location | Notes |
|-------|----------|-------|
| Continuity/state | `modules/continuity_*`, `character_state_*` | Full ContinuityManager tree |
| Perception | `modules/perception_audibility*` | Eligibility/redaction unchanged |
| Validation | `modules/response_validation*`, `issue240_*` | `make_agent_identifier` → `domain.character_cards` |
| Memory | `modules/memory_layer/`, `app_memory_summary` | V2 MemoryService unchanged API |
| Knowledge compile | `modules/canonical_compile_*`, `continuity_state_canon` | KnowledgeService unchanged |
| Scene grounding | `modules/scene_grounding.py` | continuity_context_projector consumer |

---

## 11. Persistence decision

**Option A — moved now.** `session_manager.py` + `cross_session_memory_policy.py` in `v2/domain/modules/`. Default session path uses `domain.paths.sessions_data_dir()` (repo-stable, not `__file__`-relative).

---

## 12. Narrator formatter decision

`prompt_builders.build_narrator_render_prompt` moved with validation/formatting cluster. V2 `kernel.prepare_narrator_context` unchanged call site (import path only).

---

## 13. V2 import migration

All `v2/domain_api/*.py` files now use:

```python
from domain.bootstrap import ensure_domain_paths
ensure_domain_paths()
```

**Remaining `rp_app` references in V2 production:** **zero** (static audit test).

---

## 14. V1 reverse-dependency migration

`autogen_rp/python/rp_app/*.py` (except `character_loader`) → thin shims delegating to `v2/domain/modules/` with `sys.modules` registration. V1 imports unchanged module names.

---

## 15. AutoGen/Streamlit-free proof

- `test_domain_modules_no_autogen_streamlit_imports` — AST scan of `v2/domain/modules/`
- `test_import_domain_without_autogen_in_subprocess` — subprocess import smoke
- Scoped claim: **permanent V2 domain library has no AutoGen/Streamlit/DSH dependency**

---

## 16. Test migration

| Suite | Result |
|-------|--------|
| `v2/tests/test_domain_library_m12_2.py` | 4 new tests |
| Existing V2 suites | 106 passed |
| V2 Node | 51 passed |
| V1 targeted (loader, continuity, grounding + known presence) | 85 passed, 1 known failure |

---

## 17. Known presence regression

`test_descriptive_exit_updates_authoritative_presence_state` — **unchanged known failure**, not introduced by M12.2.

---

## 18. Repository hygiene

- No duplicate implementations (single source in `v2/domain/modules/`)
- V1 shims are legacy-only with removal condition: M12.3 orchestration fence
- `scripts/m12_2_extract_domain.py`, `scripts/m12_2_fix_shims.py` — migration tooling retained
- Data paths centralized in `domain.paths`

---

## 19. Package-boundary result

```text
v2/domain_api → v2/domain (bootstrap + modules)
legacy V1 rp_app shims → v2/domain/modules
v2/rp_runtime ↔ Domain Host HTTP
```

---

## 20. M12.3 readiness

V2 no longer reaches into `rp_app` for domain semantics. Remaining `rp_app` tree is V1 orchestration (turn_runner, app.py, UI, model_client). **Ready to fence** after M12.3 governance review.

Residual: `character_loader` shim (V1 AutoGen) stays until agent factory fully legacy-fenced.

---

## 21. Validation

```text
python -m pytest v2/tests/ -q                         → 106 passed
cd v2/rp_runtime && npm test                          → 51 passed
pytest autogen_rp/python/tests/test_character_loader.py \
     test_continuity_manager.py test_scene_grounding.py → 85 passed
known: test_descriptive_exit_updates_authoritative_presence_state → 1 failed (pre-existing)
```

---

## 22. Architecture verdict

**Validated as designed**

---

## 23. Next recommended slice

**M12.3 — Fence legacy V1 orchestration** (`turn_runner`, `app.py`, UI, model_client) into `legacy/v1-orchestration/`. Do not implement without Governance review.
