# V2 Repository Retirement — M13.6 Investigation Tooling + Active Documentation Rehome

**Status:** Complete  
**Date:** 2026-08-18  
**M13.5 anchor:** `5cf9ec8`  
**M13.6 implementation HEAD:** `894ceac`

**Objective:** Rehome active investigation tooling and current Holy Grail documentation from the historical `autogen_rp` container into neutral `tools/` and `docs/` locations without altering product behavior.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `5cf9ec8` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

**Pre-slice validation baseline:** 358 domain / 152 v2 (1 xfail) / 70 rp_runtime.

---

## 2. Pre-M13.6 autogen_rp residual inventory

**65 tracked files** under `autogen_rp/`:

| Category | Count | Classification |
|----------|-------|----------------|
| `python/scripts/` | 41 | **A** active investigation tooling |
| `docs/` (HG) | 8 | **B** active documentation |
| `docs/switcher.json` | 1 | **D** upstream AutoGen docfx residue |
| `python/README.md`, `RP_SETUP_TODO.md` | 2 | **B** / **C** (TODO → archive) |
| `RP_Sedup_pompt_audit1/` | 5 | **C** historical investigation audits |
| `tools/` | 3 | **A** maintenance tooling |
| `AGENTS.md` | 1 | **B** → repo root |
| `deepseek_config.yaml` | 1 | **C** → v1-runtime archive |
| `.gitignore` ×2, `README.md` | 3 | **F** container shell |

**No tracked `rp_app/`** remained (removed M12.4).

---

## 3. Investigation script classification

| Disposition | Count | Notes |
|-------------|-------|-------|
| **Move to `tools/investigation/`** | 40 | All former `autogen_rp/python/scripts/*.py` except `_archive_paths.py` |
| **Generalize path helper** | 1 | `_archive_paths.py` → `tools/_repo_paths.py` |
| **Delete** | 1 | `_archive_paths.py` (superseded) |

**rp_app-dependent scripts (30):** Retained as investigation source; require deleted V1 modules to execute fully. Archive-reading comparators (e.g. `compare_*`) work without `rp_app`.

---

## 4. Tool classification

| Script | Disposition |
|--------|-------------|
| `issue86_inventory_pass.py` | → `tools/maintenance/` |
| `issue88_tranche1_prepare.py` | → `tools/maintenance/` |
| `issue88_tranche2_duplicate_plan.py` | → `tools/maintenance/` |

---

## 5. Documentation classification

| Item | Disposition |
|------|-------------|
| `architecture.md`, `audit-workflows.md`, `code-style.md`, `cross_session_memory.md`, `repo-map.md`, `rp-data-layout.md`, `scene-grounding-layer.md`, `testing.md` | → `docs/` (**B**) |
| `RP_SETUP_TODO.md` | → `governance/archive/planning/` (**C**) |
| `RP_Sedup_pompt_audit1/*` | → `governance/archive/investigation-audits/` (**C**) |
| `switcher.json` | **Deleted** (**D**) |
| `AGENTS.md` | → repository root (**B**) |
| `autogen_rp/README.md` | Rewritten as retirement pointer (**F**) |

---

## 6. Final active tooling layout

```text
tools/
  _repo_paths.py          # REPO_ROOT, DATA_DIR, FIXTURES_DIR, VALIDATION_RUNS_ARCHIVE, resolve_rp_audits_dir
  investigation/          # 40 investigation CLIs + helpers
  maintenance/            # issue86/88 inventory utilities
```

---

## 7. Final active documentation layout

```text
docs/                     # current technical/product docs (10 files incl. pre-existing)
AGENTS.md                   # repo-root AI assistant rules (from autogen_rp/)
governance/archive/         # historical evidence, planning, V1 runtime
```

---

## 8. Scripts/tools moved

- **40** investigation scripts → `tools/investigation/`
- **3** maintenance scripts → `tools/maintenance/`
- Path helper → `tools/_repo_paths.py` (+ thin re-export in `tools/investigation/_repo_paths.py`)

---

## 9. Historical scripts/docs archived or retained

| Path | Action |
|------|--------|
| `governance/archive/planning/RP_SETUP_TODO.md` | Archived |
| `governance/archive/investigation-audits/RP_Sedup_pompt_audit1/` | Archived (5 files) |
| `governance/archive/v1-runtime/deepseek_config.yaml` | Archived |
| Historical governance (M13.1–M13.5) | Unchanged |

---

## 10. Obsolete files deleted

| File | Reason |
|------|--------|
| `autogen_rp/docs/switcher.json` | Upstream AutoGen docfx version switcher |
| `autogen_rp/python/scripts/_archive_paths.py` | Superseded by `tools/_repo_paths.py` |
| `autogen_rp/python/README.md` | Superseded by `tools/investigation/README.md` |

---

## 11. Active-reference migration

Updated: `README.md`, `ARCHITECTURE_OVERVIEW.md`, `MODULE_INDEX.md`, `PACKET_CONTRACTS.md`, `SCENARIO_VALIDATION_FRAMEWORK.md`, `docs/issue-bootstrap-profiles.md`, `docs/core-operating-invariants.md`, `docs/rp-data-layout.md` (header + layout), `governance/archive/validation-runs/README.md`, `v2/domain/tests/test_issue242_wave0_overlay_classifier.py`, `v2/tests/test_validation_runs_archive_m13_5.py`, `.gitignore`.

---

## 12. Archive-helper/path treatment

`_archive_paths.py` eliminated. **`tools/_repo_paths.py`** is the single neutral helper:

- `REPO_ROOT`, `DATA_DIR`, `FIXTURES_DIR`, `VALIDATION_RUNS_ARCHIVE`
- `resolve_rp_audits_dir()` — `data/rp_audits` with legacy fallback
- `resolve_data_path()` — maps legacy `data/issueNNN` → `data/fixtures/issueNNN`

Investigation scripts import via `tools/investigation/_repo_paths.py` re-export shim.

---

## 13. rp_app residue treatment

**No tracked `rp_app/`** files. Scripts retain `LEGACY_RP_APP` import path for transitional reference only. **rp_app is gone** from the working tree.

---

## 14. Container metadata/gitignore treatment

| Item | Treatment |
|------|-----------|
| `autogen_rp/.gitignore` | **Retained** — local legacy data/venv ignore rules until container deletion |
| `autogen_rp/python/.gitignore` | **Retained** — same |
| Root `.gitignore` | Added `tools/maintenance/issue86_*.json`, `issue88_*.json` |
| `AGENTS.md` | Moved to repo root; paths updated |

---

## 15. Script execution/import proof

| Check | Result |
|-------|--------|
| `compare_participation_calibration_ab.py --help` | **OK** |
| `compare_willow_departure_experiment.py --help` | **OK** |
| `issue86_inventory_pass.py` | Runs; exits 1 when `data/rp_audits` absent (expected) |
| `test_investigation_tooling_m13_6.py` | **5 passed** |

---

## 16. Product-behavior guardrail confirmation

**No changes** to `v2/domain`, `v2/domain_api`, `v2/rp_runtime`, `v2/ui`, data migration semantics, or runtime services.

---

## 17. M13.1 compatibility status

**Retained.** `data_migration.py`, `legacy_data_dir()`, `HG_DATA_DIR` unchanged.

---

## 18. Full validation results

| Suite | Post-M13.6 |
|-------|------------|
| `v2/domain/tests` | **358 passed** |
| `v2/tests` | **157 passed**, 1 xfailed |
| `v2/rp_runtime npm test` | **70 passed** |

(+5 M13.6 integrity tests vs pre-slice 152 v2 baseline.)

---

## 19. Post-M13.6 autogen_rp inventory

**4 tracked files:**

| File | Role |
|------|------|
| `autogen_rp/.gitignore` | Local residue ignore rules |
| `autogen_rp/python/.gitignore` | Local residue ignore rules |
| `autogen_rp/README.md` | Retirement pointer |

**Prevents container deletion:** gitignore shells preserving legacy local-path conventions for `autogen_rp/python/data/` until M13.7 reconciles ignore rules at repo root.

---

## 20. Clean-V2 assessment

| Layer | Location |
|-------|----------|
| Production | `v2/` |
| Tests | `v2/domain/tests/`, `v2/tests/` |
| Data | `data/` |
| Investigation tooling | `tools/investigation/` |
| Maintenance tooling | `tools/maintenance/` |
| Active docs | `docs/`, `AGENTS.md` |
| Historical evidence | `governance/archive/` |

> Does any active project material remain conceptually owned by the historical AutoGen container?

**No.**

---

## 21. Final-container readiness

**Yes** — one bounded slice can delete the `autogen_rp/` container after:

1. Merging essential `autogen_rp/.gitignore` rules into root `.gitignore` (legacy local data paths).
2. Verifying no local developer workflow depends on `autogen_rp/python/` directory existing.

No additional active tooling/docs rehome required.

---

## 22. Challenge/refinement

| Question | Answer |
|----------|--------|
| Only active tooling moved? | **Yes** — dead upstream residue deleted |
| Historical scripts preserved as history? | **Yes** — rp_app-dependent scripts kept with documented limitation |
| Junk-drawer avoided? | **Yes** — `investigation/` vs `maintenance/` split |
| Current vs historical docs separated? | **Yes** |
| History rewritten? | **No** — archived docs unchanged in substance |
| Archive paths stable? | **Yes** |
| Script assumptions updated? | **Yes** — `DATA_DIR` / `FIXTURES_DIR` |
| Gitignore safe? | **Yes** — maintenance JSON ignored at new path |
| rp_app gone? | **Yes** |
| Production untouched? | **Yes** |

**Architecture verdict:** **Validated as designed**

---

## 23. Recommended next bounded slice

**M13.7 — final `autogen_rp` container retirement:** merge residual gitignore rules into root `.gitignore`, delete `autogen_rp/` tracked shell (3 files), verify local legacy data path documentation. Do not combine with new feature work.

---

## 24. Repository state

| Field | Value |
|-------|-------|
| Implementation commit | `894ceac` — `feat(m13.6): rehome investigation tooling and active docs` |
| Branch | `main` |
| Pre-slice HEAD | `5cf9ec8` |
