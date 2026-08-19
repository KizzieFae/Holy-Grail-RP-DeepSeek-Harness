# V2 Repository Retirement — M13.1 `HG_DATA_DIR` + Physical Data Rehome + Session Migration

**Status:** Complete  
**Date:** 2026-08-18  
**M13.3 anchor:** `4d429cc`  
**M13.1 completion HEAD:** `c83010f` (implementation)

**Objective:** Establish a Holy Grail-owned canonical data root (`data/`), introduce `HG_DATA_DIR`, physically rehome tracked production assets, and migrate existing local sessions/memory/knowledge from the legacy `autogen_rp/python/data/` tree without creating a second empty session universe.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `4d429cc` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |

---

## 2. Pre-M13.1 data/path inventory

| Category | Legacy path | Consumer | Git |
|----------|-------------|----------|-----|
| Character cards | `autogen_rp/python/data/autogen_characters/` | `CharacterCardLoader`, setup catalog | gitignored (local) |
| Scene templates | `autogen_rp/python/data/scene_templates/` | `SceneTemplateManager`, openers | tracked (20 files) |
| Retrieval pilot | `autogen_rp/python/data/retrieval/` | `CompiledIndexRetrievalProvider`, M12.7 | tracked |
| Issue/eval fixtures | `autogen_rp/python/data/evaluation/`, `issue227/`, `issue240/`, `issue29_*` | offline eval / tests | tracked |
| Sessions | `autogen_rp/python/data/sessions/` | `SessionManager` → `SessionRepository` | gitignored (local) |
| Cross-scope memory | `sessions/_cross_scope_memory/{scope}.json` | `CrossScopeMemoryRepository` | gitignored |
| Scope knowledge | `sessions/_scope_knowledge/{scope}.json` | `ScopeKnowledgeRepository` | gitignored |

**Prior path resolution:**

- `v2/domain/paths.py` → `autogen_python_data_dir()` defaulting to legacy root
- `v2/rp_runtime/src/lib/runtime-config.mjs` → `HG_SESSIONS_DIR` or legacy sessions path
- No `HG_DATA_DIR` before M13.1

**M9 snapshot semantics:** `setup_snapshot` embeds deep copies of character cards and template metadata at session creation; reopen does not re-read live card/template files for snapshotted fields.

---

## 3. Final canonical data-root architecture

```text
repo/data/                         # HG_DATA_DIR default
├── characters/                    # gitignored user cards
├── scene_templates/               # tracked authored templates
├── retrieval/                     # tracked pilot manifest + compiled index
├── fixtures/                      # tracked eval/issue fixtures
│   ├── evaluation/
│   ├── issue227/
│   ├── issue240/
│   ├── issue29_investigation_schedules/
│   └── progression_simulation_scenarios/  # gitignored when present locally
└── sessions/                      # gitignored runtime persistence
    ├── *.json
    ├── _session_index.json
    ├── _cross_scope_memory/
    └── _scope_knowledge/
```

**One canonical default universe:** production loaders resolve `data/` (or explicit env overrides). Legacy `autogen_rp/python/data/` is **migration source only**, not a permanent dual-read path.

---

## 4. `HG_DATA_DIR` / override precedence

| Variable | Precedence | Resolves to |
|----------|------------|-------------|
| `HG_DATA_DIR` | optional unified root | explicit path, else `repo/data/` |
| `HG_SESSIONS_DIR` | **overrides sessions only** when set | explicit path; bypasses `HG_DATA_DIR/sessions` |
| `HG_RETRIEVAL_INDEX_PATH` | unchanged (M12.7) | explicit compiled index file |

**Central resolver:** `v2/domain/paths.py`

- `holy_grail_data_dir()` — canonical root
- `characters_data_dir()`, `scene_templates_data_dir()`, `fixtures_data_dir()`, `sessions_data_dir()`
- `legacy_data_dir()` — migration source only
- `autogen_python_data_dir()` — deprecated alias → `legacy_data_dir()`

**Runtime:** `v2/rp_runtime/src/lib/runtime-config.mjs` — `defaultDataDir()`, `defaultSessionsDir()`, `domainHostSpawnEnv()` propagates `HG_DATA_DIR` when unset.

---

## 5. Physical assets moved (git)

| From | To |
|------|-----|
| `autogen_rp/python/data/scene_templates/` | `data/scene_templates/` |
| `autogen_rp/python/data/retrieval/` | `data/retrieval/` |
| `autogen_rp/python/data/evaluation/` | `data/fixtures/evaluation/` |
| `autogen_rp/python/data/issue227/` | `data/fixtures/issue227/` |
| `autogen_rp/python/data/issue240/` | `data/fixtures/issue240/` |
| `autogen_rp/python/data/issue29_investigation_schedules/` | `data/fixtures/issue29_investigation_schedules/` |

Root `.gitignore` updated to gitignore `data/*` with exceptions for tracked subtrees (mirrors prior `autogen_rp` data policy).

---

## 6. Existing-session migration mechanism

**Module:** `v2/domain/data_migration.py`

**Trigger:** `ensure_data_migrated()` called from canonical path accessors (not when `HG_SESSIONS_DIR` is explicit).

**Policy:**

1. If `data/.hg_data_migration_v1.json` marker exists with `version >= 1`, skip.
2. For each category, copy legacy → canonical **only when** canonical subdir is empty and legacy has entries.
3. Write marker with migrated/skipped categories and timestamps.
4. **Non-destructive:** legacy local tree is not deleted after success.
5. **No permanent legacy read fallback** in loaders.

**Categories migrated:** characters, scene_templates, retrieval, fixtures/*, sessions (including `_cross_scope_memory` and `_scope_knowledge` under sessions).

---

## 7. Migration idempotency / failure behavior

| Case | Behavior |
|------|----------|
| Re-run after success | Marker short-circuits; no duplicate copies |
| Canonical already populated | Category skipped (no overwrite) |
| Legacy empty (clean install) | Marker written; no migration noise |
| Partial legacy content | Only empty canonical categories receive copies |
| Legacy absent | Skipped categories; canonical install proceeds normally |

---

## 8. Character/template snapshot compatibility

Verified: sessions created before migration retain `setup_snapshot.character_cards` and template identity after reopen. Live card edits under `data/characters/` do not reinterpret historical snapshots (M9 frozen setup).

---

## 9–11. Preservation proofs (automated)

`v2/tests/test_data_migration_m13_1.py` (13 tests):

| Guarantee | Covered |
|-----------|---------|
| Legacy session discoverable after migration | yes |
| User transcript preserved | yes |
| Setup snapshot preserved | yes |
| Cross-scope memory preserved | yes |
| Scope knowledge preserved | yes |
| Opening history preserved | yes |
| Idempotent migration | yes |
| No duplicate sessions on re-run | yes |
| New sessions write to canonical only | yes |
| Explicit `HG_DATA_DIR` | yes |
| `HG_SESSIONS_DIR` precedence | yes |
| Snapshot isolation from live cards | yes |
| Clean install without legacy | yes |

---

## 12. Retrieval-data treatment

| Class | Treatment |
|-------|-----------|
| Production pilot (`data/retrieval/`) | **Moved** (tracked) |
| `HG_RETRIEVAL_INDEX_PATH` | **Unchanged** |
| Test/eval fixtures | **Moved** under `data/fixtures/` |
| `validation_runs/` evidence | **Not moved** (historical) |

---

## 13. Active old-path residue audit

| Reference | Classification |
|-----------|----------------|
| `v2/domain/paths.py` `legacy_data_dir()`, `autogen_python_data_dir()` | **Transitional migration** — remove when legacy tree retired |
| `v2/domain/data_migration.py` | **Transitional migration** — remove after operator migration window |
| `autogen_rp/python/data/` (local operator content) | **Legacy source** — not deleted by M13.1 |
| `autogen_rp/.gitignore` data rules | **Legacy local** — still applies to old path if present |
| Governance/docs historical path strings | **Historical evidence** |
| `autogen_rp/python/tests/` scene-template path updates | **Active tests** — now use `scene_templates_data_dir()` |

**Active defects:** none identified in V2 production path resolution post-M13.1.

---

## 14. Tests added/changed

| File | Change |
|------|--------|
| `v2/tests/test_data_migration_m13_1.py` | **Added** — migration proofs |
| `v2/tests/test_session_setup.py` | `characters_data_dir()` |
| `v2/tests/test_authored_knowledge_m11_1.py` | `characters_data_dir()` |
| `v2/tests/test_retrieval_index_m12_7.py` | `holy_grail_data_dir()` / `characters_data_dir()` |
| `autogen_rp/python/tests/test_scene_template*.py` | `scene_templates_data_dir()` |

---

## 15. Validation results

| Command | Result |
|---------|--------|
| `python -m pytest v2/tests/ -q` | **146 passed, 1 xfailed** (descriptive-exit; unchanged) |
| `cd v2/rp_runtime && npm test` | **62 passed, 1 failed** (`real-inference.test.mjs` — live DeepSeek credential/environment; unrelated to M13.1) |
| `python -m pytest autogen_rp/python/tests/ -q` | **358 passed** |
| `v2/tests/test_data_migration_m13_1.py` | **13 passed** |

---

## 16. Production startup/restart smoke

`HolyGrailRuntimeSupervisor` health-gated Domain Host startup: **pass** (`supervisor.test.mjs`).  
`domainHostSpawnEnv()` now sets `HG_DATA_DIR` for Domain Host child when unset.

---

## 17. Clean-V2 classification

| Item | Class |
|------|-------|
| `data/` + `HG_DATA_DIR` | **Permanent architecture** |
| Tracked templates/retrieval/fixtures | **Migrated active assets** |
| `data_migration.py` + marker | **Transitional** |
| `legacy_data_dir()` / `autogen_python_data_dir()` | **Transitional** |
| `autogen_rp/python/tests/`, `validation_runs/` | **Test/evidence** (unchanged location) |
| `autogen_rp/python/.venv` | **Transitional dev tooling** |
| Legacy `autogen_rp/python/data/` local files | **Operator residue** — eligible for manual cleanup later |

**Architecture verdict:** **One canonical default data universe** under `repo/data/`; legacy path is not a parallel production read location.

---

## 18. Transitional fallback and removal condition

No permanent dual-read fallback was introduced. One-time copy migration only.

**Removal condition (future M13 slice):** delete `data_migration.py`, marker handling, and `legacy_data_dir()` after:

1. governance confirms operator migration window elapsed, and  
2. no active docs/tests require legacy path as live default.

---

## 19. Challenge/refinement findings

| Finding | Resolution |
|---------|------------|
| Neutral-domain tests hardcoded legacy template path | Updated to `scene_templates_data_dir()` |
| `HG_SESSIONS_DIR` must remain independent | Preserved — explicit override bypasses migration hook |
| Session snapshotted setup must survive card rehome | Proven via migration tests |
| Do not commit local sessions/characters | Root `.gitignore` mirrors prior policy under `data/` |

---

## 20. Recommended next bounded M13 slice

**M13.2 — relocate `autogen_rp/python/tests/` → `v2/domain/tests/`** (neutral-domain contract tests co-located with domain). Do not start without Governance review.

---

## 21. Repository state

| Field | Value |
|-------|-------|
| Implementation commit | `c83010f` |
| Governance HEAD | `bc850c4` |
| Branch | `main` |
| Working tree | clean post-commit |
