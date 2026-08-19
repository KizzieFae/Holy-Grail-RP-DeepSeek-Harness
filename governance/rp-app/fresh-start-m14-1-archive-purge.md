# Fresh-Start M14.1 — Archive and Tombstone Purge

**Status:** Complete  
**Date:** 2026-08-18  
**M14 investigation anchor:** `d32664a`  
**Pre-slice HEAD:** `d32664a`  
**M14.1 implementation HEAD:** 797f8bfabcbeb2524bf161252eab1cf35ebda2e9

**Assigned workflow weight:** standard  
**Effective workflow weight:** full

**Objective:** Delete obsolete V1/legacy archives, M12 one-shot scripts, and namespace tombstones without changing product/runtime behavior. Re-home bootstrap authority references to current docs.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Branch | `main` |
| Pre-slice HEAD | `d32664a` |
| Working tree | clean at activation |
| M14 governing record | `fresh-start-residue-investigation-m14.md` |

---

## 2. Pre-deletion candidate inventory

| Candidate | Historical only | Current authority | Bootstrap dep | Tool/test dep | Active doc dep | Final action |
|-----------|-----------------|-------------------|---------------|---------------|----------------|--------------|
| `governance/archive/v1-runtime/` (4) | Yes | Was cited by bootstrap | **Was** — re-pointed | No production | **Was** — re-pointed | **DELETE** |
| `governance/archive/validation-runs/` (81) | Yes | No | No | `VALIDATION_RUNS_ARCHIVE` default output | README/SCENARIO refs | **DELETE** + re-point output to `data/investigation_runs/` |
| `governance/archive/investigation-audits/` (5) | Yes | No | No | No | No | **DELETE** |
| `governance/archive/planning/` (1) | Yes | No | No | No | ARCHITECTURE ref removed | **DELETE** |
| `governance/archives/issue-215/` (19) | Yes | No | No | No | No | **DELETE** |
| `governance/archives/issue-240/` (2) | Yes | No | No | No | No | **DELETE** |
| `scripts/m12_*.py` (5) | Yes | No | No | No CI/test refs | No | **DELETE** |
| `legacy/__init__.py` (1) | Yes | No | No | No imports | No | **DELETE** |
| `v2/tests/test_validation_runs_archive_m13_5.py` | N/A | No | No | Subject deleted | No | **DELETE** |

**Retained (M14.2 boundary):** `legacy_data_dir()`, `data_migration.py`, `ensure_data_migrated()`, `.gitignore autogen_rp/`, `LEGACY_RP_APP` tooling constant.

---

## 3. Authority / bootstrap dependency findings

| Mechanism | Prior dependency | M14.1 resolution |
|-----------|------------------|------------------|
| `docs/issue-bootstrap-profiles.md` Full profile | `governance/archive/v1-runtime/ARCHITECTURE.md`, `AUDIT_DOCUMENTATION.md` | → `ARCHITECTURE_OVERVIEW.md`, `docs/architecture.md`, `docs/audit-workflows.md`, `docs/rp-data-layout.md` |
| `docs/core-operating-invariants.md` | v1-runtime ARCHITECTURE | → `ARCHITECTURE_OVERVIEW.md` |
| `AGENTS.md` instruction priority | `governance/archive/v1-runtime/` | → `docs/` |
| `governance/policies/` | No archive paths | Unchanged |
| `governance/rp-app/issue-tracking-workflow.md` | No archive paths | Unchanged |
| M12/M13 retirement governance records | Historical links to archives | **Unchanged** (immutable program records) |

No stateless-resume source depended on deleted archives.

---

## 4. Deletions

| Category | Files deleted |
|----------|---------------|
| `governance/archive/` | 91 |
| `governance/archives/` | 20 |
| `scripts/m12_*` | 5 |
| `legacy/__init__.py` | 1 |
| `v2/tests/test_validation_runs_archive_m13_5.py` | 1 |
| **Total** | **118** |

---

## 5. Structural reference updates (minimal)

| File | Change |
|------|--------|
| `tools/_repo_paths.py` | `VALIDATION_RUNS_ARCHIVE` → `data/investigation_runs/` (gitignored) |
| `docs/issue-bootstrap-profiles.md` | Bootstrap reads → current docs |
| `README.md`, `ARCHITECTURE_OVERVIEW.md`, `MODULE_INDEX.md` | Remove dead archive pointers |
| `docs/audit-workflows.md`, `docs/rp-data-layout.md`, `docs/core-operating-invariants.md` | Authority → current docs |
| `SCENARIO_VALIDATION_FRAMEWORK.md`, `PACKET_CONTRACTS.md` | Output/history wording |
| `tools/investigation/README.md`, `governance/README.md`, `AGENTS.md` | Structural |
| `.gitignore` | Removed obsolete `governance/archive/validation-runs/` noise rules |

---

## 6. Validation

| Suite | Result |
|-------|--------|
| `python -m pytest v2/domain/tests/ -q` | **358 passed** |
| `python -m pytest v2/tests/ -q` | **154 passed, 1 xfailed** (−6 archive integrity tests removed) |
| `cd v2/rp_runtime && npm test` | **70 passed** |

Structural proofs:

- `git ls-files governance/archive governance/archives` → **0**
- `git ls-files scripts` → **0**
- `git ls-files legacy` → **0**
- No production import of deleted paths

---

## 7. Post-slice terminology (tracked `git grep -l` counts)

| Pattern | Count | Classification |
|---------|-------|----------------|
| `autogen_rp` | 71 | M14.2 migration compat + M14.3 tooling + historical governance |
| `AutoGen` | 37 | Historical governance + comments |
| `legacy` | 88 | Domain semantics + M14.2 migration + docs |
| `rp_app` | 68 | M14.3 investigation scripts + historical governance |
| `turn_runner` | 33 | Historical governance + docs |
| `scripts/m12` | 2 | Historical governance only |

---

## 8. M14.2 boundary confirmation

**Untouched:** `v2/domain/paths.py` (`legacy_data_dir`, `ensure_data_migrated`), `v2/domain/data_migration.py`, `.gitignore autogen_rp/`, migration tests (`test_data_migration_m13_1.py`).

---

## 9. Remaining M14 work

| Slice | Scope |
|-------|-------|
| **M14.2** | Migration compatibility sunset |
| **M14.3** | `LEGACY_RP_APP` investigation cleanup; retirement tests |
| **M14.4** | Comprehensive current-doc fresh-start rewrite |
| **M14.5** | Optional `v2/` promotion |

---

## 10. Architecture verdict

**Archive and tombstone purge complete.** Repository tree visibly cleaner; product behavior unchanged. Git history preserves deleted evidence.

---

## 11. Repository state

| Implementation commit | `797f8bfabcbeb2524bf161252eab1cf35ebda2e9` |
| Branch | `main` |
