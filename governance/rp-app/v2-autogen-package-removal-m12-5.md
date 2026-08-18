# V2 AutoGen Package Removal — M12.5

**Status:** Complete  
**Date:** 2026-08-18  
**M12.4 anchor:** `9830f3d`  
**M12.5 completion HEAD:** `TBD` (see §27)

**Objective:** Remove obsolete vendored AutoGen packages and prove Holy Grail V2 operates without any AutoGen dependency.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-removal HEAD | `9830f3d` (M12.4) |
| `origin/main` | aligned at activation |
| Workflow | standard / effective **full** |

---

## 2. Remaining AutoGen dependency inventory (pre-removal)

| Consumer | Type | Imports AutoGen? | Executed today? | Required? | Action |
|----------|------|------------------|-----------------|-----------|--------|
| `v2/domain`, `v2/domain_api`, `v2/rp_runtime` | Production | No | Yes | N/A | None |
| `autogen_rp/python/tests/` (35 modules) | Domain tests | No | Yes | No | Retained |
| `autogen_rp/python/packages/*` | Vendored framework | Yes (internal) | No | No | **Deleted** |
| `autogen_rp/python/samples/*` | Upstream samples | Yes | No | No | **Deleted** |
| `autogen_rp/python/docs/*` | Upstream docs | Text only | No | No | **Deleted** |
| `validation_runs/issue249,251/run_*` experiments | Historical LLM scripts | Yes | No | No | **Deleted** (6 files) |
| `deepseek_example.py`, `test_deepseek.py` | Dead V1 examples | Yes | No | No | **Deleted** |
| `autogen_rp/python/rp_app/` | Deprecated namespace | No (shims) | No | No | **Deleted** |
| `autogen_rp/dotnet/` | Upstream .NET AutoGen | N/A | No | No | **Deferred M12.8** |
| `autogen_rp/.github/workflows/` | Upstream CI | N/A | No | No | Inert (not repo root CI) |
| Governance / validation markdown | Evidence | Text only | No | No | Retained |

---

## 3. Vendored-package inventory (pre-removal)

| Package | Files (approx.) | Production import | Action |
|---------|-----------------|-------------------|--------|
| `autogen-core` | 164 | No | Deleted |
| `autogen-ext` | 251 | No | Deleted |
| `autogen-agentchat` | 106 | No | Deleted |
| `autogen-studio` | 228 | No | Deleted |
| `agbench` | 56 | No | Deleted |
| `autogen-test-utils` | 7 | No | Deleted |
| `component-schema-gen` | 6 | No | Deleted |
| `magentic-one-cli` | 7 | No | Deleted |
| `pyautogen` | 4 | No | Deleted |
| `autogen-magentic-one` | 2 | No | Deleted |

**Total:** 831 files (~7.3 MB) under `autogen_rp/python/packages/`

---

## 4. Consumer classification

- **A Production:** None (confirmed M12.4)
- **B Permanent tests:** None — 358 domain tests use `domain.bootstrap` only
- **C Active tools:** None requiring AutoGen
- **D Historical evidence:** `validation_runs/*.md`, governance — retained inert
- **E Dead residue:** packages, samples, docs, examples, `uv.lock`, uv workspace config — deleted
- **F Documentation-only:** Updated active docs; historical records unchanged

---

## 5. Surviving test dependency assessment

All **358** `autogen_rp/python/tests/` pass without AutoGen. No test imports `autogen_agentchat`, `autogen_core`, or `autogen_ext`.

Added `v2/tests/test_m12_5_autogen_removal.py` with AST import scan + isolated subprocess proof (`python -I`, `PYTHONNOUSERSITE=1`).

---

## 6. Script/tool dependency assessment

| Item | Result |
|------|--------|
| `autogen_rp/python/scripts/` | No AutoGen imports |
| `tools/validate_beat_shift_checkpoint.py` | Referenced deleted `rp_app` — **deleted** |
| Validation experiment runners | 6 AutoGen LLM scripts deleted; neutral helpers retained |

---

## 7. Historical evidence treatment

Markdown reports, audit JSON, and governance records mentioning AutoGen retained unchanged. Archived evidence does not participate in import paths.

---

## 8. Bootstrap/path cleanup

Removed:
- `uv` workspace (`[tool.uv.workspace]`, `[tool.uv.sources]`)
- `autogen-vendored-tests` dependency group
- `poe` tasks targeting vendored packages
- `fixup_generated_files.py`, `run_task_in_pkgs_if_exist.py`
- `shared_tasks.toml`, `uv.lock`

Retained: `domain.bootstrap.ensure_domain_paths()` (V2 neutral).

---

## 9. Vendored packages removed

Deleted entire `autogen_rp/python/packages/` plus `samples/`, `docs/`, `templates/`, and obsolete bootstrap tooling.

---

## 10. Dependency declaration cleanup

`autogen_rp/python/pyproject.toml` replaced with minimal Holy Grail domain-test configuration (pytest only).

---

## 11. Samples/examples cleanup

All `autogen_rp/python/samples/` deleted (upstream vendor examples, no Holy Grail product value).

---

## 12. Active documentation cleanup

- `autogen_rp/python/README.md` — V2-first domain test guide
- `MODULE_INDEX.md` — M12.5 banner
- `v2/domain/__init__.py` — removed `rp_app` shim reference
- `v2/domain/modules/perception_audibility.py` — removed stale `rp_app/ARCHITECTURE.md` pointer

---

## 13. Production dependency proof

| Check | Result |
|-------|--------|
| V2 production AutoGen imports | **0** |
| `v2/domain` AutoGen imports | **0** |
| Domain test AutoGen imports | **0** |
| Active script AutoGen imports | **0** (path-name false positives only) |

---

## 14. Clean import/startup proof

`test_m12_5_autogen_removal.py::test_domain_imports_in_isolated_subprocess_without_packages` runs `python -I` with `PYTHONNOUSERSITE=1` — no vendored packages directory, no user-site fallback. Domain imports succeed.

---

## 15. Behavioral validation

| Command | Result |
|---------|--------|
| `python -m pytest v2/tests/ -q` | **116 passed, 1 xfailed** |
| `cd v2/rp_runtime && npm test` | **51 passed** |
| `python -m pytest autogen_rp/python/tests/ -q` | **358 passed** |

Preserved xfail: `test_presence_descriptive_exit_regression.py` (unchanged).

---

## 16. Surviving neutral-domain validation

**358 passed** — unchanged count from M12.4 baseline.

---

## 17. V2 production smoke

Node suite includes supervisor → Domain Host → DSH startup paths; all **51 passed**.

---

## 18. Repository-wide residue audit

Executable AutoGen Python imports outside deleted vendor tree: **0**.

Residual textual references: governance (historical), `autogen_rp` path names, `autogen_characters` data directory, `autogen_rp/dotnet/` (deferred).

---

## 19. autogen_rp residual assessment

| Category | Remains |
|----------|---------|
| Data/assets | `autogen_rp/python/data/` |
| Domain tests | `autogen_rp/python/tests/` |
| Scripts | Investigation utilities (no AutoGen) |
| Evidence | `validation_runs/`, markdown audits |
| Vendor | `autogen_rp/dotnet/` only (deferred M12.8) |
| Name | **Historical container** — no AutoGen Python packages |

---

## 20. rp_app namespace decision

**Deleted.** Empty deprecated namespace removed in M12.5. No imports depended on it (tests use `domain.bootstrap`). Removal condition met.

---

## 21. Dependency-retirement metrics

| Metric | Before | After |
|--------|--------|-------|
| Vendored package dirs | 10 | **0** |
| Vendor files (python/packages) | 831 | **0** |
| Samples/docs/templates | 296 | **0** |
| `rp_app` namespace | shell | **removed** |
| Executable AutoGen imports (product/tests/scripts) | 0 | **0** |
| Total files removed (M12.5 script) | — | **~1,682** |

---

## 22. AutoGen retirement status

| Question | Answer |
|----------|--------|
| Does Holy Grail production require AutoGen? | **No** |
| Do authoritative automated tests require AutoGen? | **No** |
| Do active development/validation tools require AutoGen? | **No** |
| Are any AutoGen Python packages still vendored? | **No** |

**AutoGen dependency retirement is complete** (Python). `autogen_rp/dotnet/` remains upstream residue for M12.8.

---

## 23. Revised M12 sequence

Original plan advanced vendor removal from M12.7 to M12.5 (completed).

**Recommended next slice:** **M12.6 — Opening/bootstrap V2 parity** (or explicit governance deferral). Remaining: opening/bootstrap, retrieval-index, player/settings UX, `autogen_rp` tree rehome (M12.8).

---

## 24. Clean-V2 classification

| Tier | Contents |
|------|----------|
| **Permanent production** | `v2/domain`, `v2/domain_api`, `v2/rp_runtime`, `v2/ui` |
| **Transitional** | `autogen_rp/python/data/`, `autogen_rp/python/tests/` |
| **Evidence** | `validation_runs/`, governance, archived audits |
| **Vendor** | `autogen_rp/dotnet/` only (non-Python, deferred) |
| **Deprecated namespace** | `rp_app` — **removed** |

---

## 25. Challenge/refinement

- No production path required AutoGen ✓
- Domain tests framework-free ✓
- Package bootstrap removed ✓
- Isolated subprocess proof addresses global-install fallback ✓
- Holy Grail data preserved ✓
- No unexplained executable imports ✓

---

## 26. Architecture verdict

**Validated as designed**

---

## 27. Repository state

Recorded at commit time.

---

## 28. Next recommended migration slice

**M12.6 — Opening/bootstrap V2 parity** (product capability; do not implement without Governance review).
