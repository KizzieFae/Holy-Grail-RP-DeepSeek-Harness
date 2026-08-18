# V2 Repository Retirement & Hygiene — M13 Investigation

**Status:** Investigation complete (design only — no moves/deletions)  
**Date:** 2026-08-18  
**M12.8 functional-completion anchor:** `37c563e`  
**M13 investigation HEAD:** `489852c`

**Objective:** Design the final repository-retirement plan after V2 functional completion. **No implementation in M13.**

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD / `origin/main` | `37c563e` |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |
| Bootstrap profile | full V2 retirement/hygiene investigation |
| Production launcher | `Launch-Holy-Grail-V2.bat` → `v2/rp_runtime` (`npm run app`) |
| V1 runtime | **deleted** (M12.4); `autogen_rp/python/rp_app/` **absent** on disk and untracked |

### Validation baseline (unchanged during investigation)

| Suite | Result |
|-------|--------|
| V2 Python | **133 passed, 1 xfailed** |
| V2 Node | **63 passed** |
| Neutral domain (`autogen_rp/python/tests/`) | **358 passed** |

---

## 2. `autogen_rp` residual inventory

Counts are **git-tracked** unless noted **(local)**. Sizes exclude **(local)** `.venv` (~1.7 GB on developer machines).

| Subtree | Tracked files | ~Size | Purpose | Executable? | Consumers |
|---------|---------------|-------|---------|-------------|-----------|
| `autogen_rp/dotnet/` | 745 | ~40 MB | Microsoft AutoGen .NET SDK, samples, tests, website | Yes (.NET) | **None** in Holy Grail V2 |
| `autogen_rp/python/tests/` | 57 | 0.3 MB | Neutral-domain pytest contracts (35 modules → 358 tests) | Test-only | `pytest autogen_rp/python/tests` |
| `autogen_rp/python/data/` (tracked) | 61 | <0.2 MB | Authored fixtures: scene templates, retrieval pilot, issue schedules, evaluation baselines | Data | `v2/domain` loaders via `domain.paths` |
| `autogen_rp/python/data/` **(local gitignored)** | ~1,625 | ~14 MB | User sessions (~1,420), character cards (~22), rp_audits (~82), misc | Data | Production V2 via default paths |
| `autogen_rp/python/validation_runs/` | 81 | 0.9 MB | Historical validation markdown/JSON evidence | No (artifacts) | Governance / manual reference |
| `autogen_rp/python/scripts/` | 41 | 0.2 MB | Issue investigation runners (pre-V1-deletion era) | Yes (Python) | **No** production path; optional manual audits |
| `autogen_rp/python/pyproject.toml` | 1 | — | Pytest harness for neutral-domain tests | Config | `pytest` root |
| `autogen_rp/python/README.md` | 1 | — | Documents test/data role post-M12.5 | Docs | Developers |
| `autogen_rp/python/.venv/` **(local)** | — | ~1.7 GB | Python venv used by `runtime-config.mjs` default | Yes | Supervisor Domain Host spawn |
| `autogen_rp/docs/` | 31 | small | AutoGen fork docs + rp-data-layout (partially stale) | Docs | Root README links |
| `autogen_rp/.github/`, `.devcontainer/`, `.azure/` | ~25 | small | Upstream AutoGen CI/devcontainer | CI | **Not** Holy Grail V2 CI |
| `autogen_rp/` root | ~10 | small | AutoGen README, LICENSE, AGENTS.md | Docs | Historical |

**Deleted / absent (confirmed):**

- `autogen_rp/python/rp_app/` — removed M12.4; not on disk
- `autogen_rp/python/packages/` — removed M12.5

---

## 3. Residual classification

| Class | Items |
|-------|-------|
| **A — Permanent product data** | Scene templates (tracked); retrieval pilot manifest/index (tracked); character cards + sessions + scope stores **(local, gitignored)** |
| **B — Permanent behavioral tests** | `autogen_rp/python/tests/` — 35 modules, 358 tests, pure `v2/domain` imports |
| **C — Historical evidence** | `validation_runs/`, local `rp_audits/`, issue investigation JSON under `data/issue*` |
| **D — Active dev tooling** | `autogen_rp/python/.venv` (local); `v2/rp_runtime` npm scripts (production) |
| **E — Obsolete vendor** | **`autogen_rp/dotnet/`** entire tree; AutoGen `.github`/`.devcontainer` under `autogen_rp/` |
| **F — Transitional naming** | `domain.paths.autogen_python_data_dir()`; `runtime-config.mjs` autogen paths; `SessionManager` name |
| **G — Unknown / low value** | Some `scripts/` runners — verify no unique logic before delete |

---

## 4. Production data-path inventory

| Data category | Current path | Consumer | Desired permanent path | Migration notes |
|---------------|--------------|----------|------------------------|-----------------|
| Character cards | `autogen_rp/python/data/autogen_characters/` | `CharacterCardLoader`, `OpenerManager`, catalog API | `data/characters/` | **Local user content**; copy or symlink; keep gitignored |
| Scene templates | `autogen_rp/python/data/scene_templates/` | `SceneTemplateManager` | `data/scene_templates/` | 20 tracked files — move in git |
| Template openers | co-located `*_initial_message.json` | `OpenerManager` | same tree under `data/scene_templates/` | Move with templates |
| Sessions | `autogen_rp/python/data/sessions/` | `SessionManager` → `SessionRepository` | `data/sessions/` | **Critical** — see §6 |
| Session index | `.../sessions/_session_index.json` | `SessionManager` | `data/sessions/_session_index.json` | Move with sessions |
| Cross-scope memory | `.../sessions/_cross_scope_memory/` | `SessionRepository` | `data/sessions/_cross_scope_memory/` | Colocated with sessions |
| Scope knowledge | `.../sessions/_scope_knowledge/` | `KnowledgeService` | `data/sessions/_scope_knowledge/` | Colocated with sessions |
| Retrieval index | env `HG_RETRIEVAL_INDEX_PATH` (default example under `data/retrieval/compiled/`) | `CompiledIndexRetrievalProvider` | `data/retrieval/` | Tracked pilot files move; env path update in docs |
| Semantic eval profiles | `data/evaluation/semantic_eval_profiles_v1.json` | `semantic_eval_profiles.py` | `data/evaluation/` or `data/fixtures/evaluation/` | Small tracked fixture |
| Issue schedules | `data/issue29_*`, `data/issue240/` | Tests / scripts | `data/fixtures/issues/` or `governance/archive/` | Test fixtures vs evidence split |
| RP audits | `data/rp_audits/` **(local)** | None in V2 production | `governance/archive/audits/` or delete local copies | Not product runtime |
| Progression scenarios | `data/progression_simulation_scenarios/` **(local)** | `progression_simulation_scenarios.py` | `data/fixtures/progression/` if retained | Low production relevance |

**Central resolver today:** `v2/domain/paths.py` → `autogen_python_data_dir()`.

**Runtime default sessions:** `v2/rp_runtime/src/lib/runtime-config.mjs` → `HG_SESSIONS_DIR` or `autogen_rp/python/data/sessions`.

---

## 5. Recommended final data layout

**Recommendation:** repo-root **`data/`** (framework-neutral, not under `v2/`).

```text
data/
├── characters/          # gitignored user/authored cards (not committed)
├── scene_templates/     # tracked authored templates + opener sidecars
├── retrieval/           # tracked pilot manifest + compiled index example
├── fixtures/            # tracked test fixtures (issue schedules, evaluation JSON)
└── sessions/            # gitignored runtime persistence (entire tree)
    ├── _session_index.json
    ├── _cross_scope_memory/
    ├── _scope_knowledge/
    └── hg-session-*.json
```

**Rationale:**

- Separates **product data** from **versioned code** (`v2/`)
- Matches mental model in root README / PRD
- `v2/` remains implementation; `data/` is deployment/content
- Avoids nesting user sessions inside a path named `autogen_rp`

**Optional env unification:**

```text
HG_DATA_DIR  →  repo/data  (default)
HG_SESSIONS_DIR  →  ${HG_DATA_DIR}/sessions  (override remains supported)
```

Do **not** introduce `HG_DATA_DIR` until M13.1 implementation slice; design supports it.

---

## 6. Existing-session migration implications

| Question | Answer |
|----------|--------|
| Must existing sessions keep working? | **Yes** — local operator sessions under current path must not silently orphan |
| Automatic vs one-time migration? | **One-time copy + fallback read** recommended for M13.1 |
| Env override today? | **Yes** — `HG_SESSIONS_DIR` on Domain Host spawn (`runtime-config.mjs`, `domain_api/__main__.py`) |
| Two session stores risk? | **High** if only code default changes without moving/copying local `sessions/` |
| Recommended transition | (1) Introduce `HG_DATA_DIR` with default **new** path; (2) on startup, if new dir empty and legacy dir has files, **log + read fallback** from legacy for one release; (3) optional migration script copies `sessions/`, `_cross_scope_memory/`, `_scope_knowledge/`; (4) remove fallback after governance sign-off |

**Session snapshots protect reopen semantics** — JSON files are self-contained; path change does not invalidate `setup_snapshot` inside files.

**Do not** require users to reselect identity after migration if files are moved wholesale.

---

## 7. Character/template asset migration implications

| Component | Impact |
|-----------|--------|
| `CharacterCardLoader` | Default dir from `characters_data_dir()` — update once in `paths.py` |
| `SceneTemplateManager` / `OpenerManager` | Same for `scene_templates_data_dir()` |
| Catalog APIs | Unaffected if loaders point to new path |
| Existing sessions | **Stable** — `setup_snapshot` embeds card copies at create time |
| New sessions | Must find cards at new canonical path |
| Tests | Update hardcoded `autogen_rp/python/data/autogen_characters` in ~4 `v2/tests` files |
| Gitignore | Move rules from `autogen_rp/.gitignore` `/python/data/*` to root `.gitignore` `data/characters/`, `data/sessions/` |

---

## 8. Neutral-domain test inventory

**Current:** 35 test modules, **358 tests**, all import `v2/domain/modules` via `domain.bootstrap.ensure_domain_paths()`.

| Category | Modules (approx) | Action |
|----------|------------------|--------|
| **Permanent domain contracts** | continuity, perception, scene_template, scene_grounding, character_move_ingress, response_validation, memory_layer, tension_pacing, issue regression guards | **Retain** — move to `v2/domain/tests/` |
| **Redundant with `v2/tests`** | Partial overlap on session setup, knowledge (M11–M12 slices cover integration) | **Keep domain unit tests** — different granularity; dedupe only if proven identical |
| **Historical / issue-specific** | `test_issue242_wave0_*`, `test_i251_*`, audit manifest tests | **Retain** as domain contracts until issue closed |
| **Obsolete V1** | None remaining in the 35-file set (V1 orchestration tests deleted M12.4) | — |
| **Fixtures/tools** | `test_pytest_root_collection.py` | Retain as harness guard |

**No `rp_app` / `turn_runner` tests remain** on disk.

---

## 9. Final test-layout recommendation

```text
v2/
├── tests/                    # Domain Host + integration (existing 22 modules, 133 tests)
├── domain/
│   └── tests/                # Neutral domain contracts (moved from autogen_rp/python/tests)
└── rp_runtime/
    └── tests/                # Node/DSH (existing 63 tests)
```

**Pytest entry points after migration:**

```sh
python -m pytest v2/domain/tests v2/tests -q
cd v2/rp_runtime && npm test
```

Retire `autogen_rp/python/pyproject.toml` after test move; add `v2/pyproject.toml` or root `pyproject.toml` if needed.

---

## 10. Known descriptive-exit regression placement

| Location | Status |
|----------|--------|
| `v2/tests/test_presence_descriptive_exit_regression.py` | **Authoritative** — `strict=True` xfail |
| `autogen_rp/python/tests/test_presence_initiative_regressions.py` | **Absent** (removed with suite trim) |

No duplicate to remove. Do not fix behavior in retirement work.

---

## 11. Validation/evidence archive assessment

| Path | Classification | Recommendation |
|------|----------------|----------------|
| `validation_runs/` (81 tracked) | Historical reports + JSON experiment outputs | **Archive** → `governance/archive/validation-runs/` (markdown + small JSON only) |
| `validation_runs/**/_run_*.py` | Dead generated runners | **Delete** (already gitignored patterns in root `.gitignore`) |
| `python/scripts/` (41) | Investigation utilities | **Archive** → `governance/archive/scripts/` or `tools/archive/`; delete if redundant with governance docs |
| `data/rp_audits/` (local) | V1 audit JSON | **Archive** sample fixtures to `governance/archive/v1-runtime/audits/`; do not commit bulk |

---

## 12. Audit-data assessment

| Item | Role | Recommendation |
|------|------|----------------|
| `data/rp_audits/` | V1 runtime-generated audit trees | **Not** production V2; local/gitignored |
| Tracked audit manifest tests | Domain contract for audit JSON shape | Keep tests; fixtures under `data/fixtures/audits/` if needed |
| Audit UI | Optional product enhancement | **Out of scope** |

---

## 13. .NET tree assessment

| Check | Result |
|-------|--------|
| Holy Grail V2 references | **0** |
| Build/test in Holy Grail CI | **No** |
| Holy Grail-specific modifications | **0** (grep: no `Holy Grail` in `autogen_rp/dotnet`) |
| Tracked files | **745** (~40 MB incl. samples) |
| Non-sample core | **598 files** (~8.6 MB) |

**Verdict: DELETE** — pure upstream Microsoft AutoGen vendor residue.

Samples under `dotnet/samples/` (147 files, ~31 MB) included in deletion.

---

## 14. SessionManager assessment

| Aspect | Current state |
|--------|---------------|
| Location | `v2/domain/modules/session_manager.py` |
| Responsibility | JSON session file codec, `_session_index.json`, load/save/list |
| Consumers | `v2/domain_api/session_repository.py` only (production) |
| V1 assumptions | Docstring still says "RP app"; uses `sessions_data_dir()` |
| V2 metadata | Written by `SessionRepository._build_session_payload` (`v2_host_state` key) |

**Rename value:** **Low–medium** — clarifies persistence vs domain authority, but **not** a behavioral blocker.

**If renamed (M13.4):** prefer `JsonSessionStore` or `FileSessionPersistence` — document as **internal** to `SessionRepository`.

---

## 15. SessionRepository / persistence end-state

```text
SessionRepository     ← domain-facing authority (LiveSession, memory, knowledge, dedup)
    ↓
File persistence    ← JSON + index (today: SessionManager)
```

**Both layers remain useful.** `SessionRepository` should stay the only import surface for `domain_api`. Lower layer is a file codec — could be inlined later, but separation aids testing.

**Smallest clean end-state:** rename persistence helper + move default data root; **do not** merge repository and file codec in hygiene work.

---

## 16. Historical path-helper inventory

| Reference | Classification |
|-----------|----------------|
| `v2/domain/paths.py` `autogen_python_data_dir()` | **F — transitional**; rename to `holy_grail_data_dir()` in M13.1 |
| `v2/rp_runtime/src/lib/runtime-config.mjs` | **F** — sessions + venv under `autogen_rp/python/` |
| `v2/tests/*` hardcoded `autogen_rp/python/data/...` | **F** — update with data move |
| `v2/README.md` `cd autogen_rp/python` | **Stale docs** — M13.5 |
| Root `README.md` rp_app pointers | **Stale docs** — M13.5 |
| `autogen_rp/docs/rp-data-layout.md` | **Stale** — rewrite for `data/` layout |
| Governance historical records | **Keep** — do not rewrite M12 anchors |

No active stale absolute `E:\CascadeProjects\...` paths in permanent V2 code.

---

## 17. Configuration / environment-path recommendation

| Variable | Today | Recommendation |
|----------|-------|----------------|
| `HG_SESSIONS_DIR` | Override session root | **Retain** |
| `HG_PYTHON_EXECUTABLE` | Override Python for Domain Host | **Retain**; default venv path → `/.venv` or `v2/.venv` after rehome |
| `HG_DOMAIN_HOST_URL` | Supervisor sets for DSH | **Retain** |
| `HG_RETRIEVAL_INDEX_PATH` | Optional compiled index | **Retain** |
| `RP_RETRIEVED_CONTEXT_INDEX` | Legacy alias | **Retain** until docs drop it |
| `HG_DATA_DIR` | — | **Add in M13.1** as optional unified root defaulting to `repo/data/` |

Avoid extra indirection without the physical data move.

---

## 18. Python project/container cleanup assessment

After test + data rehome:

| Item | Action |
|------|--------|
| `autogen_rp/python/pyproject.toml` | **Delete** (pytest root moves) |
| `autogen_rp/python/README.md` | **Delete** or replace with stub redirect |
| `autogen_rp/python/scripts/` | Archive/delete |
| `autogen_rp/python/validation_runs/` | Archive |
| Entire `autogen_rp/` | **Delete** when python + dotnet + docs removed |

---

## 19. Documentation cleanup requirements (M13.5)

| Doc | Issue |
|-----|-------|
| Root `README.md` | Still describes V1 `rp_app`, AutoGen monorepo |
| `MODULE_INDEX.md` | References `rp_app` modules |
| `ARCHITECTURE_OVERVIEW.md` | May reference V1 runtime |
| `v2/README.md` | Points to `autogen_rp/python` for tests |
| `autogen_rp/docs/rp-data-layout.md` | Wrong paths |

Historical governance (M12.x) — **do not edit**.

---

## 20. Archive-layout recommendation

```text
governance/archive/
├── v1-runtime/              # existing (ARCHITECTURE, AUDIT_DOCUMENTATION)
├── validation-runs/         # from autogen_rp/python/validation_runs/
├── scripts/                 # investigation scripts (optional)
└── audits/                  # small curated audit JSON samples only
```

Single archive root under `governance/archive/` — avoid parallel `evidence/` junk drawer unless large binary assets require it.

---

## 21. Gitignore implications

Current: `autogen_rp/.gitignore` ignores `/python/data/*` with exceptions for templates, retrieval pilot, issue fixtures.

**After move to `data/`:**

```gitignore
data/characters/
data/sessions/
data/rp_audits/
!data/scene_templates/**
!data/retrieval/**
!data/fixtures/**
```

Ensure **no private character cards or session JSON** committed. Retain retrieval pilot tracked files.

---

## 22. Launcher/path implications

`Launch-Holy-Grail-V2.bat` only `cd v2/rp_runtime && npm run app` — **no direct data paths**.

Indirect dependencies:

- `runtime-config.mjs` default sessions + venv → update in M13.1
- Domain Host `PYTHONPATH=v2` → unchanged
- Streamlit `HG_APP_API_URL` → unchanged

**No hardcoded checkout paths** should be introduced.

---

## 23. Final repository target

```text
Holy-Grail-RP-DeepSeek-Harness/
├── Launch-Holy-Grail-V2.bat
├── data/                          # product + user data (partially tracked)
│   ├── characters/                # gitignored
│   ├── scene_templates/           # tracked
│   ├── retrieval/                 # tracked pilot
│   ├── fixtures/                  # tracked test fixtures
│   └── sessions/                  # gitignored runtime
├── v2/
│   ├── domain/
│   │   ├── modules/
│   │   └── tests/                 # 358 neutral-domain tests
│   ├── domain_api/
│   ├── rp_runtime/
│   ├── ui/
│   └── tests/                     # integration / Domain Host
├── governance/
│   ├── rp-app/
│   └── archive/
├── pyproject.toml                 # optional unified pytest root
└── README.md                      # Holy Grail RP (post-retirement)
```

**`autogen_rp/` — eliminated.**

---

## 24. `v2/` directory decision

**Recommendation: Keep `v2/` through retirement slices.**

| Option | Verdict |
|--------|---------|
| Keep `v2/` | **Yes for M13.x** — avoids double-move of code + tests + docs |
| Promote to root | **Defer** to post-retirement hygiene (M14?) after `autogen_rp` deleted |
| Rename now | **No** — high churn, zero user value mid-retirement |

Decide promotion only when repository contains no `autogen_rp` and docs say "Holy Grail RP" without migration framing.

---

## 25. Product naming recommendation

| Context | Name |
|---------|------|
| User-facing / docs (post-retirement) | **Holy Grail RP** |
| Internal path / historical governance | **V2** acceptable until promotion |
| Repository name | Keep `Holy-Grail-RP-DeepSeek-Harness` |

Drop "V2" from user-facing Streamlit title in M13.5 doc pass, not in M13 investigation.

---

## 26. Retirement/hygiene matrix (primary deliverable)

| Current path | Role | Destination | Action | Prerequisite | Validation |
|--------------|------|-------------|--------|--------------|------------|
| `autogen_rp/dotnet/` | Upstream AutoGen .NET | — | **delete** | None | 358+133+63 tests |
| `autogen_rp/.github/`, `.devcontainer/` | Upstream CI | — | **delete** | dotnet deletion | — |
| `autogen_rp/python/data/scene_templates/` | Authored templates | `data/scene_templates/` | **move** | `paths.py` + gitignore | session setup tests |
| `autogen_rp/python/data/retrieval/` | Retrieval pilot | `data/retrieval/` | **move** | env docs | M12.7 tests |
| `autogen_rp/python/data/evaluation/`, `issue*` | Test fixtures | `data/fixtures/` | **move** | test path updates | neutral + v2 |
| `autogen_rp/python/data/autogen_characters/` | User cards (local) | `data/characters/` | **move** (local) | migration note in README | catalog API smoke |
| `autogen_rp/python/data/sessions/` | Runtime persistence (local) | `data/sessions/` | **move** (local) | `HG_DATA_DIR` + fallback | reopen tests |
| `autogen_rp/python/tests/` | Domain contracts | `v2/domain/tests/` | **move** | pytest root | 358 tests |
| `autogen_rp/python/pyproject.toml` | Test config | `v2/pyproject.toml` or root | **replace** | test move | pytest |
| `autogen_rp/python/validation_runs/` | Evidence | `governance/archive/validation-runs/` | **archive** | — | — |
| `autogen_rp/python/scripts/` | Investigation | `governance/archive/scripts/` | **archive/delete** | script audit | — |
| `autogen_rp/python/.venv` | Dev venv (local) | `.venv` or `v2/.venv` | **relocate** (manual) | runtime-config default | supervisor smoke |
| `v2/domain/paths.py` | `autogen_python_data_dir` | `holy_grail_data_dir` + `HG_DATA_DIR` | **rename** | data move slice | all suites |
| `SessionManager` | File persistence | optional rename | **rename** (optional) | M13.4 | session repository tests |
| Root README, MODULE_INDEX | Stale V1 refs | updated docs | **update** | M13.5 | — |
| `data/rp_audits/` (local) | V1 audits | archive sample | **archive/delete** | — | — |

---

## 27. Recommended phased cleanup sequence

| Slice | Scope | Risk |
|-------|-------|------|
| **M13.3** | Delete `autogen_rp/dotnet/` + upstream `autogen_rp/.github`, `.devcontainer`, `.azure` | **Low** |
| **M13.1** | Introduce `HG_DATA_DIR` + move tracked `data/` + update `paths.py`, `runtime-config.mjs`, gitignore; local session migration script + legacy fallback | **Medium** |
| **M13.2** | Move `autogen_rp/python/tests/` → `v2/domain/tests/`; pytest root; delete `autogen_rp/python/` shell | **Low–medium** |
| **M13.4** | Optional `SessionManager` rename; venv default path; remove legacy path fallbacks | **Low** |
| **M13.5** | Root docs hygiene; product naming; consider `v2/` promotion governance | **Low** |

Each slice: full test suite green; product launcher smoke.

---

## 28. First recommended implementation slice

**M13.3 — Delete `autogen_rp/dotnet/` and upstream AutoGen CI/devcontainer residue.**

| Criterion | Why this slice |
|-----------|----------------|
| Structural value | **745 tracked files** (~40 MB) of zero-use vendor tree |
| Behavioral risk | **None** — no V2 import or CI reference |
| Validation | Standard 358 + 133 + 63 suites |
| Interference | **Independent** of data/test path moves — avoids moving files twice |

**Do not implement without Governance review.**

---

## 29. Functional-completion guardrail

Confirmed: this plan does **not** reopen DSH orchestration, MemoryService, KnowledgeService, player/settings, opening, retrieval, or Director/Character/Narrator lifecycle. Hygiene only.

---

## 30. Optional enhancement separation

Explicitly **out of scope** for repository retirement:

- Narrator semantic retry
- Audit/debug UI
- Advanced Streamlit role selectors
- Descriptive-exit presence fix
- Vector retrieval

---

## 31. Challenge/refinement

| Question | Answer |
|----------|--------|
| Moving for names vs architecture? | Data move improves architecture (separates product data from dead `autogen_rp` container) |
| Existing sessions survive? | Yes, with explicit migration/fallback in M13.1 |
| Character cards stay private? | Yes — gitignore moves with `data/characters/` |
| Snapshots protect sessions? | Yes — embedded `setup_snapshot` |
| All 358 tests worth retaining? | **Yes** — already trimmed to domain-only set; no V1 tests remain |
| `.NET` unique? | **No** |
| SessionManager rename worthwhile? | **Optional** — defer to M13.4 |
| Keep `v2/`? | **Yes** until retirement complete |
| Move paths twice? | **Avoid** — delete dotnet first; single data move in M13.1 |
| `HG_DATA_DIR` reduces cost? | **Yes** — one abstraction for M13.1 |
| Evidence vs fixtures separated? | **Yes** — `governance/archive/` vs `data/fixtures/` |
| New developer clarity? | **Yes** after `autogen_rp/` gone |
| Each slice runnable? | **Yes** — mandated validation per slice |
| Optional features mixed in? | **No** |

---

## 32. Architecture verdict

**Repository-retirement architecture established** — one focused operational question remains for Governance: **exact local session migration UX** (automatic copy vs documented manual step) when `data/sessions/` goes live.

---

## 33. Next recommended action

Governance review of **M13.3** (.NET/vendor deletion) as first implementation slice.
