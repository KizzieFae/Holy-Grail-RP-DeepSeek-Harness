# V2 Repository Retirement — M13.4 Production Python Environment Rehome

**Status:** Complete  
**Date:** 2026-08-18  
**M13.2 anchor:** `8a4e961`  
**M13.4 implementation HEAD:** *(set at commit)*

**Objective:** Remove the active production dependency on `autogen_rp/python/.venv` by establishing a framework-neutral canonical Python environment at the repository root and updating runtime interpreter resolution.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `8a4e961` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

---

## 2. Pre-M13.4 Python interpreter/path inventory

| Location | Role | Classification |
|----------|------|----------------|
| `v2/rp_runtime/src/lib/runtime-config.mjs` `defaultPythonExecutable()` | Production default | **Production** — pointed at `autogen_rp/python/.venv` |
| `domain-host-process.mjs` | Spawn + existence check | **Production** |
| `hg-app.mjs` | Streamlit python resolution | **Production** |
| `HG_PYTHON_EXECUTABLE` | Explicit override | **Production** |
| `tests/helpers/domain-api.mjs` | Re-exports `defaultPythonExecutable` | **Test** |
| `Launch-Holy-Grail-V2.bat` | Node-only launcher | **Production** (no direct venv path) |
| `autogen_rp/python/.venv` (local) | Historical dev venv | **Local residue** |
| Governance/docs citing old path | Historical records | **Historical** |

**No CI workflows** referenced the old venv.

---

## 3. Canonical Python environment decision

**Location:** repository root `.venv/`

| Criterion | Assessment |
|-----------|------------|
| Windows-friendly | **Yes** — `Scripts/python.exe` |
| Repo-relative | **Yes** — resolved from `repoRoot` in `runtime-config.mjs` |
| Decoupled from `autogen_rp` | **Yes** |
| Matches common Python convention | **Yes** |
| Works with `HG_PYTHON_EXECUTABLE` | **Yes** |

**Rejected:** `v2/.venv/` — unnecessarily couples interpreter to V2 subtree while Domain Host already uses `PYTHONPATH=v2`.

---

## 4. Python project/dependency ownership

**Option A — single root `pyproject.toml`** adopted for canonical environment provisioning.

| File | Role |
|------|------|
| `pyproject.toml` (repo root) | Canonical Holy Grail Python project metadata + dev dependency group |
| `v2/domain/pyproject.toml` | Retained for `cd v2/domain && pytest` convenience (`testpaths = ["tests"]`) |

Both share the **same** repo-root `.venv`. No second environment introduced.

Domain Host runtime uses `PYTHONPATH=v2` with stdlib-only production imports (no pip runtime deps required for spawn).

---

## 5. Interpreter-resolution precedence

```text
supervisor/options.pythonExecutable (explicit per call)
    ↓
HG_PYTHON_EXECUTABLE
    ↓
<repo>/.venv/{Scripts/python.exe | bin/python}
    ↓
clear error if missing (no legacy fallback, no PATH python fallback)
```

---

## 6. Local legacy-venv migration posture

**Option A — require explicit provisioning** of repo-root `.venv`.

- No git move of `autogen_rp/python/.venv` (path-sensitive; gitignored).
- No permanent fallback to legacy venv.
- Operators recreate: `python -m venv .venv` from repository root.
- Missing interpreter error includes provisioning hint referencing `v2/README.md`.

---

## 7. Implementation changes

| File | Change |
|------|--------|
| `v2/rp_runtime/src/lib/runtime-config.mjs` | `canonicalVenvRoot()`, `canonicalPythonExecutable()`, `pythonExecutableForVenvRoot()`; default → repo `.venv` only |
| `domain-host-process.mjs` | Provisioning hint on missing canonical interpreter |
| `pyproject.toml` | **New** — root Python project |
| `.gitignore` | `.venv/` at repo root |
| `v2/README.md`, `README.md`, `autogen_rp/python/README.md` | Active setup docs |
| `v2/domain/pyproject.toml` | Description references root venv |
| `v2/rp_runtime/tests/runtime-config.test.mjs` | **New** — resolution proofs |

---

## 8. Test-helper migration

`tests/helpers/domain-api.mjs` continues to re-export `defaultPythonExecutable` from shared `runtime-config.mjs` — single resolver policy for production and integration tests.

---

## 9. Launcher behavior

`Launch-Holy-Grail-V2.bat` unchanged — invokes `npm run app`; supervisor resolves Python via updated `runtime-config.mjs`.

---

## 10. Validation

| Command | Result |
|---------|--------|
| `python -m pytest v2/domain/tests/ -q` | **358 passed** |
| `python -m pytest v2/tests/ -q` | **146 passed, 1 xfailed** (descriptive-exit; unchanged) |
| `cd v2/rp_runtime && npm test` | **70 passed** (includes 7 new `runtime-config` tests) |

Supervisor health-gated Domain Host startup: **pass** (canonical `.venv`).

---

## 11. Residue audit

Active production code references to `autogen_rp/python/.venv`: **0**

| Remaining reference | Classification |
|---------------------|----------------|
| Governance M13/M6 records | Historical |
| `CHECKPOINT_BASELINE_DSH.md` | Historical |
| `autogen_rp/python/README.md` | Documents legacy residue |

---

## 12. Clean-V2 assessment

**Does active production runtime depend on the `autogen_rp` container?** **No.**

Production startup path: launcher → Node supervisor → canonical repo `.venv` → Domain Host.

**Remaining `autogen_rp` purposes:** validation evidence, investigation scripts, historical docs, optional local legacy `.venv` residue.

---

## 13. M13.1 guardrail

Unchanged — `HG_DATA_DIR`, migration marker, session/data tests green.

---

## 14. Challenge/refinement

| Question | Answer |
|----------|--------|
| Production reliance on historical container removed? | **Yes** for interpreter resolution |
| Exactly one normal local Python environment? | **Yes** — repo-root `.venv` |
| Second Python project proliferated? | **No** — root owns venv; domain pyproject is test convenience |
| `HG_PYTHON_EXECUTABLE` preserved? | **Yes** |
| PATH python fallback removed? | **Yes** — avoids masking missing venv |
| Windows paths with spaces proven? | **Yes** — unit test |
| M13.1 untouched? | **Yes** |

**Architecture verdict:** **Validated as designed**

---

## 15. Recommended next bounded slice

**Archive `autogen_rp/python/validation_runs/` → `governance/archive/validation-runs/`** (evidence rehome). Do not combine with script rehome or container deletion.

---

## 16. Repository state

*(Updated at commit.)*
