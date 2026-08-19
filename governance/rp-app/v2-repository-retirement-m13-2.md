# V2 Repository Retirement — M13.2 Neutral-Domain Test Rehome

**Status:** Complete  
**Date:** 2026-08-18  
**M13.1 anchor:** `6ecb7a2`  
**M13.2 implementation HEAD:** *(set at commit)*

**Objective:** Relocate the 358-test neutral-domain pytest suite from historical `autogen_rp/python/tests/` to `v2/domain/tests/`, co-locating permanent domain behavioral contracts with the domain library.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `6ecb7a2` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

---

## 2. Post-M13.1 retirement inventory (summary)

| Remaining `autogen_rp/**` (tracked) | ~146 files after M13.2 | Class |
|-------------------------------------|------------------------|-------|
| `python/validation_runs/` | ~81 | Historical evidence |
| `python/scripts/` | ~41 | Investigation tooling (non-production) |
| `python/docs/` + root docs | ~9+ | Holy Grail / historical docs |
| `python/tools/` | ~3 | Investigation utilities |
| `python/data/` (local) | gitignored | Legacy migration source (M13.1) |
| `python/.venv/` | local | Dev venv (supervisor default spawn) |
| `AGENTS.md`, `.gitignore`, etc. | small | Historical container |

**Active V2 production** no longer reads tests or tracked data from `autogen_rp/`. M13.1 migration compatibility (`data_migration.py`, `legacy_data_dir()`) **retained** — removal condition not yet satisfied (operators may still have legacy local data).

---

## 3. Selected slice: M13.2 — neutral-domain test rehome

### Rationale

| Criterion | Assessment |
|-----------|------------|
| Removes misleading boundary | **Yes** — 358 domain contracts no longer appear “under AutoGen” |
| Clear destination | `v2/domain/tests/` beside `v2/domain/modules/` |
| Behavioral risk | **Low** — tests already import `v2/domain` only |
| Strong validation | 358 + 146 + 63 suites |
| Evidence preservation | **Unchanged** — `validation_runs/` not moved |

### Alternatives considered / rejected

| Candidate | Verdict |
|-----------|---------|
| Remove M13.1 migration compatibility now | **Rejected** — legacy local data may still exist on operator machines |
| Delete entire `autogen_rp/python/` shell | **Rejected** — scripts/validation_runs still have value; too broad |
| Archive `validation_runs/` in same slice | **Rejected** — independent concern; would mix test move + evidence archive |
| `SessionManager` rename | **Deferred** — naming only; no structural dependency removed |

### Explicit exclusions

- No `data/` or migration logic changes
- No `validation_runs/` or `scripts/` moves
- No `.venv` default path change
- No `SessionManager` rename
- No product/runtime behavior changes

---

## 4. Challenge / refinement outcome

| Risk | Mitigation |
|------|------------|
| Import breakage after move | Fixed `repo_root()`-relative paths for scripts/validation_runs helpers (2 tests) |
| Obsolete `rp_app` sys.path | Removed 31 dead inserts |
| Test discovery from new cwd | `v2/domain/pyproject.toml` + `test_pytest_root_collection.py` updated |
| Evidence path strings in governance | **Preserved** historical references |

---

## 5. Implementation

| Action | Detail |
|--------|--------|
| Move | `autogen_rp/python/tests/` → `v2/domain/tests/` (57 tracked paths) |
| Move | `autogen_rp/python/pyproject.toml` → `v2/domain/pyproject.toml` |
| Clean | Remove obsolete `rp_app` `sys.path` inserts from all test modules |
| Fix | `test_i251_doctrine_alignment.py`, `test_issue242_wave0_overlay_classifier.py` → `repo_root()` paths |
| Update | `autogen_rp/python/README.md`, `v2/README.md`, `ARCHITECTURE_OVERVIEW.md`, `SCENARIO_VALIDATION_FRAMEWORK.md` |
| Update | `v2/tests/test_m12_5_autogen_removal.py` domain test path |

---

## 6. Validation

| Command | Result |
|---------|--------|
| `python -m pytest v2/domain/tests/ -q` | **358 passed** |
| `cd v2/domain && python -m pytest -q` | **358 passed** |
| `python -m pytest v2/tests/ -q` | **146 passed, 1 xfailed** (descriptive-exit; unchanged) |
| `cd v2/rp_runtime && npm test` | **63 passed** (live DeepSeek credentialed in this run) |

Supervisor smoke: included in Node suite (`supervisor.test.mjs`).

---

## 7. Residue audit

| Reference | Classification |
|-----------|----------------|
| `v2/domain/tests/` | **Permanent tests** |
| `autogen_rp/python/tests/` | **Removed** (no shim directory) |
| Governance docs citing old test path | **Historical** |
| `validation_runs/*.md` citing old test modules | **Historical evidence** |
| `legacy_data_dir()` / `data_migration.py` | **Transitional** (M13.1; retained) |
| `runtime-config.mjs` → `autogen_rp/python/.venv` | **Transitional** (next slice candidate) |

No active defects identified.

---

## 8. Clean-V2 assessment

| Layer | Location |
|-------|----------|
| Permanent production | `v2/domain_api/`, `v2/rp_runtime/`, `v2/domain/modules/` |
| Permanent domain tests | `v2/domain/tests/` |
| V2 integration tests | `v2/tests/` |
| Active data | `data/` (`HG_DATA_DIR`) |
| Historical evidence | `autogen_rp/python/validation_runs/` |
| Investigation tooling | `autogen_rp/python/scripts/` |
| Transitional | M13.1 migration, `.venv` default under `autogen_rp/python/` |

**Architecture subordination verdict:** Active Holy Grail **tests and data** are no longer organized under `autogen_rp`. Production code was already V2-local. Remaining `autogen_rp` content is **evidence, scripts, docs, and local venv** — not production architecture, but the **container name** remains misleading until a later slice retires or archives it.

---

## 9. M13.1 migration compatibility status

**Retained.** Canonical `data/` architecture unchanged. No reintroduction of legacy data root as a production read path.

---

## 10. Recommended next bounded slice

**M13.3 (revised numbering) — archive `autogen_rp/python/validation_runs/` to `governance/archive/validation-runs/`** with path-preserving references in evidence docs, OR **M13.4 — relocate default Python venv resolution** in `runtime-config.mjs` away from `autogen_rp/python/.venv`. Execute one only; do not combine.

---

## 11. Repository state

*(Updated at commit.)*
