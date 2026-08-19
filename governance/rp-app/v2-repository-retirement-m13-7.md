# V2 Repository Retirement — M13.7 Final `autogen_rp` Container Retirement

**Status:** Complete — **M13 repository retirement/hygiene program complete**  
**Date:** 2026-08-18  
**M13.6 anchor:** `efb1393`  
**M13.7 implementation HEAD:** `eb7199c`

**Objective:** Delete the final tracked `autogen_rp/` shell while preserving local privacy/data ignore protections and M13.1 migration compatibility.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `efb1393` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

**Pre-slice tracked `autogen_rp/`:** exactly 3 files (M13.6 shell).

---

## 2. Pre-M13.7 residual container inventory

| File | Role |
|------|------|
| `autogen_rp/.gitignore` | Nested ignore for legacy local tree |
| `autogen_rp/python/.gitignore` | Nested ignore for python subtree |
| `autogen_rp/README.md` | Retirement pointer |

No additional tracked files appeared.

---

## 3. Nested gitignore rule analysis

### `autogen_rp/.gitignore` (257 lines)

| Class | Examples | Disposition |
|-------|----------|-------------|
| **Already at root** | `.env`, `.venv`, `__pycache__`, `.DS_Store`, `.pytest_cache` | No merge |
| **Obsolete upstream** | `dotnet/artifacts`, `samples/`, `notebook/`, `OAI_CONFIG_LIST`, `docusaurus` | Drop |
| **Superseded by `data/`** | `/python/data/*` with fixture exceptions | Root `data/*` + exceptions already cover canonical data |
| **Still required for local legacy tree** | Entire `autogen_rp/python/data` local residue, legacy `.venv`, eval dumps | **Replaced by root `autogen_rp/` ignore** |

### `autogen_rp/python/.gitignore` (208 lines)

| Class | Examples | Disposition |
|-------|----------|-------------|
| **Duplicate Python/stdlib** | packaging, tox, mypy caches | Drop (root covers or N/A) |
| **Obsolete** | `validation_runs/**` (moved M13.5), `docs/src/reference` | Drop |
| **Useful at root** | `_val*.txt` investigation scratch | **Merged** to root `.gitignore` |

**Decision:** Do not concatenate nested files. Add **`autogen_rp/`** blanket ignore at root plus `_val*.txt`.

---

## 4. Privacy/data protections preserved

Root `.gitignore` already protects (M13.1):

- `data/*` with tracked exceptions for `scene_templates/`, `retrieval/`, `fixtures/`
- `.venv/`, `.env`, secrets patterns
- `tools/maintenance/issue86_*.json`, `issue88_*.json`

**Added M13.7:**

```gitignore
autogen_rp/          # local legacy tree (migration source; not tracked)
*_val*.txt           # headless harness scratch triggers
```

Operator-local legacy data at `autogen_rp/python/data/` remains **ignored** and **discoverable** by `legacy_data_dir()` without any tracked container.

---

## 5. Active-reference audit

| Match class | Action |
|-------------|--------|
| `legacy_data_dir()` / `data_migration.py` | **Retained** — M13.1 compatibility |
| `LEGACY_RP_APP` in `tools/_repo_paths.py` | **Retained** — investigation transitional |
| M13.5/M13.6 integrity tests asserting absence | **Retained** |
| `ARCHITECTURE_OVERVIEW.md`, `README.md`, `docs/rp-data-layout.md`, `MODULE_INDEX.md` | **Updated** to current paths |
| Historical governance/archive | **Unchanged** |

---

## 6. README/container-pointer treatment

`autogen_rp/README.md` **deleted with container**. Information already captured in:

- root `README.md` (repository layout)
- `governance/rp-app/v2-repository-retirement-m13-6.md`
- `governance/archive/v1-runtime/`

No tombstone relocated.

---

## 7. autogen_rp tracked-container deletion

```text
git rm autogen_rp/.gitignore
git rm autogen_rp/python/.gitignore
git rm autogen_rp/README.md
```

**Result:** `git ls-files autogen_rp` → empty.

---

## 8. Local legacy residue treatment

| Concept | Treatment |
|---------|-----------|
| Tracked repository container | **Removed** |
| Operator-local `autogen_rp/python/data/` | **May still exist** on disk; ignored via `autogen_rp/` |
| Operator-local old `.venv` | **May still exist**; ignored; production uses repo-root `.venv` |
| Migration | `legacy_data_dir()` computes path **without** requiring tracked files |

---

## 9. Tracked-residue proof

| Check | Result |
|-------|--------|
| `git ls-files autogen_rp` | **empty** |
| `test_autogen_rp_container_retirement_m13_7.py` | **3 passed** |
| `git status` after change | no unexpected untracked private data surfaced |

---

## 10. Production dependency proof

| Layer | Depends on tracked `autogen_rp`? |
|-------|----------------------------------|
| `v2/rp_runtime` supervisor | **No** — repo-root `.venv` |
| `v2/domain_api` Domain Host | **No** |
| `data/` (`HG_DATA_DIR`) | **No** |
| `tools/` | **No** (historical path constants only) |
| Tests | **No** |

---

## 11. Migration/path focused validation

| Test | Result |
|------|--------|
| `legacy_data_dir()` path computation | **OK** — independent of tracked container |
| `test_data_migration_m13_1.py` | **passes** (within 358 domain suite) |
| `test_validation_runs_archive_m13_5.py` | **passes** |
| `test_investigation_tooling_m13_6.py` | **passes** |
| `runtime-config.test.mjs` (no autogen_rp venv) | **passes** |

---

## 12. Full validation results

| Suite | Post-M13.7 |
|-------|------------|
| `v2/domain/tests` | **358 passed** |
| `v2/tests` | **160 passed**, 1 xfailed |
| `v2/rp_runtime npm test` | **70 passed** |

(+3 M13.7 integrity tests vs M13.6 baseline of 157 v2 tests.)

---

## 13. Production startup smoke

`v2/rp_runtime` npm suite includes supervisor health-gated Domain Host startup (`supervisor: health-gated Domain Host startup`, `supervisor: starts DSH runtime after Domain Host healthy`) — **70/70 passed** with no `autogen_rp` directory.

---

## 14. Active documentation cleanup

Updated: `README.md`, `ARCHITECTURE_OVERVIEW.md`, `MODULE_INDEX.md`, `docs/rp-data-layout.md`, `docs/audit-workflows.md`.

Removed `autogen_rp/` from current repository layout description.

---

## 15. Final repository architecture

```text
Holy-Grail-RP-DeepSeek-Harness/
├── .venv/                 # local ignored (canonical Python env)
├── AGENTS.md
├── data/                  # HG_DATA_DIR — active product data
├── docs/                  # active technical documentation
├── governance/
│   ├── archive/           # historical evidence + V1 runtime
│   ├── policies/
│   └── rp-app/            # governance records (M13.x)
├── tools/
│   ├── _repo_paths.py
│   ├── investigation/     # offline investigation CLIs
│   └── maintenance/       # inventory/hygiene utilities
├── v2/
│   ├── domain/
│   ├── domain_api/
│   ├── rp_runtime/
│   ├── ui/
│   └── tests/
├── Launch-Holy-Grail-V2.bat
├── pyproject.toml
└── ...
```

**`autogen_rp/`:** absent from tracked architecture; may exist locally as ignored legacy residue.

---

## 16. M13.1 compatibility status

| Item | Status |
|------|--------|
| `legacy_data_dir()` | **Retained** — returns `repo_root() / "autogen_rp" / "python" / "data"` |
| `data_migration.py` | **Retained** |
| Removal condition | Independent governance decision when all operators have migrated and compatibility policy allows deletion of migration code |
| Active architectural dependence? | **No** — path computation only; not repository ownership |

---

## 17. SessionManager naming assessment

`SessionManager` / `SessionRepository` naming reflects historical V1 file-persistence vocabulary but is **functionally clear** in current V2 code (`v2/domain_api/session_repository.py`). Renaming is **cosmetic** and **not** a repository-retirement blocker. **No future M13 slice recommended** unless product documentation initiative separately warrants it.

---

## 18. v2 directory / product naming assessment

`v2/` is now a **stable product root** naming convention. Promoting/rename to unqualified paths would create large churn with minimal architectural benefit. **Defer** unless a separate product-branding initiative is authorized. Active docs may say **Holy Grail RP** while retaining `v2/` path references.

---

## 19. Remaining-work classification

| Item | Class |
|------|-------|
| M13.1 `legacy_data_dir()` migration | **Deferred migration compatibility** |
| SessionManager rename | **Cosmetic/optional hygiene** |
| `v2/` directory rename | **Cosmetic/optional hygiene** |
| Descriptive-exit xfail | **Known defect** (out of M13 scope) |
| rp_app-dependent investigation scripts | **Product enhancement / tooling restoration** (separate) |

**No required repository-retirement work remains.**

---

## 20. M13 completion decision

> Is repository retirement/hygiene complete?

**Yes — repository retirement complete with deferred migration compatibility.**

All active production, tests, data, tools, docs, and evidence live in permanent Holy Grail locations. The obsolete V1/AutoGen **tracked container is gone**. M13.1 migration compatibility remains **by design** and does not block completion.

---

## 21. Challenge/refinement

| Question | Answer |
|----------|--------|
| Still-relevant ignore rules preserved? | **Yes** — `autogen_rp/` + existing `data/*` |
| Private local data exposed? | **No** |
| Legacy migration without tracked dir? | **Yes** |
| Local vs tracked distinguished? | **Yes** |
| Active paths neutral? | **Yes** |
| Current docs accurate? | **Yes** |
| `autogen_rp` absent from architecture? | **Yes** |
| Extending cleanup beyond value? | **No** |

**Architecture verdict:** **Repository retirement complete with deferred migration compatibility**

---

## 22. Repository state

| Field | Value |
|-------|-------|
| Implementation commit | `eb7199c` — `feat(m13.7): delete final autogen_rp tracked container` |
| Branch | `main` |
| Pre-slice HEAD | `efb1393` |

---

## 23. Next step

**M13 is complete.** Do not open M13.8 for container hygiene.

Appropriate next work categories (Governance review required):

- **Normal product operation** and feature development under `v2/`
- **Known defect:** descriptive-exit presence regression (existing xfail)
- **Optional future:** M13.1 migration compatibility removal (separate governance decision)
- **Optional cosmetic:** SessionManager / `v2/` naming (low priority)
