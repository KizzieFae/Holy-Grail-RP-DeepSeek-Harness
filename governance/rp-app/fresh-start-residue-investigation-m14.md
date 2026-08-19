# Fresh-Start Repository Residue Investigation — M14

**Status:** Investigation complete (no implementation in this slice)  
**Date:** 2026-08-18  
**Investigation HEAD (pre-record):** `9e2592c`  
**Prior program anchors:** M12.8 `37c563e` · M13.7 `9e2592c` (program complete)

**Objective:** Inventory remaining V1 / legacy / AutoGen residue under the operator's stronger **fresh-start** goal — the repository should present Holy Grail RP as the current application, not as a migration from V1. Re-evaluate prior decisions to retain archives and compatibility code. **No deletions, renames, or migrations in this pass.**

**Operator goal (binding for this investigation):**

> Remove old-version/V1/legacy/AutoGen residue, obsolete folders/files/naming, transitional compatibility, and unnecessary historical references where safely possible — not merely fence or archive them.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD | `9e2592c` |
| `origin/main` | `9e2592c` (matches) |
| Working tree | **clean** (no unexpected untracked product files visible) |
| Assigned workflow weight | **standard** |
| Effective workflow weight | **full** |
| Bootstrap profile | full repository / V2 architecture + retirement history |
| M12.8 functional-completion anchor | `37c563e` |
| M13 program status | **Complete** (`v2-repository-retirement-m13-7.md`) |

### Prior-completion claims — verified

| Claim | Verified |
|-------|----------|
| Tracked `autogen_rp/` absent | **Yes** — `git ls-files autogen_rp` → 0 files |
| Production under `v2/` | **Yes** |
| Canonical data `data/` | **Yes** |
| Canonical Python env repo-root `.venv/` | **Yes** |
| Tests `v2/domain/tests/`, `v2/tests/` | **Yes** |
| Tooling `tools/` | **Yes** |
| Active docs `docs/` + `AGENTS.md` | **Yes** |
| Historical material `governance/archive/` | **Yes** — 91 tracked files |

### Material deviation from expected anchor

**None blocking.** Operator workstation retains a **local ignored** `autogen_rp/` tree (~68,574 files) — expected under M13.7 local-residue model; not tracked architecture.

---

## 2. Residue-search methodology

1. **Activation sync** — `git branch`, `rev-parse HEAD` / `origin/main`, `git status`, recent log.
2. **Tracked-file terminology scan** — `git grep -l` on patterns: `autogen_rp`, `AutoGen`, `legacy`, `rp_app`, `turn_runner`, `V1`, `v1-runtime`, `v2/`.
3. **Workspace ripgrep** — includes ignored local `autogen_rp/` for distinction (tracked vs local).
4. **Directory inventory** — `git ls-files` counts per top-level and archive subtree.
5. **Active-code inspection** — `v2/domain/paths.py`, `data_migration.py`, `tools/_repo_paths.py`, retirement tests, launchers.
6. **Validation baseline** — pytest domain, pytest integration, `npm test` in `v2/rp_runtime`.

**Classification buckets used:**

| Bucket | Meaning |
|--------|---------|
| **Active product** | Required for current Holy Grail RP operation |
| **Transitional compatibility** | Exists only for migration from retired layout |
| **Retirement regression guard** | Tests proving absence of retired paths |
| **Historical governance** | M12/M13 decision records |
| **Archived evidence** | Validation runs, V1 docs, investigation audits |
| **Obsolete one-shot tooling** | M12 extraction scripts no longer runnable |
| **Domain semantics** | `legacy` in identifiers meaning in-scene/dialogue logic, not repo V1 |
| **Local operator residue** | Ignored disk state, not repository architecture |

---

## 3. Terminology counts and classification

### Tracked-file hit counts (`git grep -l`)

| Pattern | Tracked files | Primary locus |
|---------|---------------|---------------|
| `autogen_rp` | **133** | governance (M12/M13 + archive), docs, tests, `paths.py`, `data_migration.py`, `tools/_repo_paths.py`, investigation scripts |
| `AutoGen` | **40** | governance archive + M12/M13 records + a few active comments |
| `legacy` | **100** | governance, docs, migration code, **domain logic** (`REFUSAL_LEGACY_*`, `production_legacy` eval mode) |
| `rp_app` | **129** | governance, investigation scripts (`LEGACY_RP_APP`), archive, docs |
| `turn_runner` | **39** | governance archive + M12 records + docs |
| `v2/` | **~55+ governance + pervasive product** | paths, launcher, README, cordis, tests |

### High-signal classifications

| Match class | Examples | Disposition under fresh-start |
|-------------|----------|-------------------------------|
| Migration source path | `legacy_data_dir()`, `.gitignore autogen_rp/` | **DELETE AFTER MIGRATION CHECK** |
| Broken investigation imports | `LEGACY_RP_APP` → deleted `rp_app` | **REWRITE or DELETE** scripts |
| V1 runtime archive | `governance/archive/v1-runtime/` (4 files) | **DELETE** (git history preserves) |
| Validation evidence | `governance/archive/validation-runs/` (81 files) | **DELETE** or **HISTORICAL ONLY** |
| M12 one-shot scripts | `scripts/m12_*.py` (5 files) | **DELETE** |
| Namespace tombstone | `legacy/__init__.py` | **DELETE** |
| Retirement proof tests | `test_m12_*`, `test_m13_*`, `test_autogen_rp_*` | **DELETE** after cleanup |
| Domain `legacy` tokens | `REFUSAL_LEGACY_DIALOGUE_MARKERS` | **KEEP** — not V1 residue |
| Fixture `*_v1.json` | evaluation baselines | **KEEP** — artifact version label |
| Product framing | README "V2 production", `Launch-Holy-Grail-V2.bat` | **REWRITE / RENAME** |
| `v2/` directory name | entire product tree | **INVESTIGATE FURTHER** — high churn |

---

## 4. Directory and file residue inventory

### Tracked residue attributable primarily to retired system

| Path | Tracked files | Value today | Fresh-start assessment |
|------|---------------|-------------|------------------------|
| `governance/archive/v1-runtime/` | 4 | V1 Streamlit/AutoGen docs | **D** — no operational value; git history sufficient |
| `governance/archive/validation-runs/` | 81 | Issue evidence, experiment JSON/MD, replay scripts | **C/D** — useful for audit trail only |
| `governance/archive/investigation-audits/` | 5 | 2026-03 RP setup audits | **D** |
| `governance/archive/planning/RP_SETUP_TODO.md` | 1 | Pre-M13 setup checklist | **D** |
| `governance/archives/issue-215/` | 19 | Phase adjudication packages | **C/E** — traceability only |
| `governance/archives/issue-240/` | 2 | Investigation artifacts | **C** |
| `governance/rp-app/v2-v1-*`, `v2-autogen-*`, `v2-repository-retirement-m13*` | ~20 | M12/M13 program records | **B/E** — shrink active governance surface |
| `scripts/m12_*.py` | 5 | One-time extraction/deletion automation | **C** — obsolete; references deleted paths |
| `legacy/__init__.py` | 1 | V1 namespace tombstone | **C** — pure residue |
| `.gitignore` rule `autogen_rp/` | — | Protects local legacy tree | **DELETE AFTER MIGRATION CHECK** |
| Local `autogen_rp/` (ignored) | ~68k local | Operator legacy data/tooling copy | **Not tracked** — operator may delete locally |

### Not residue (current product)

| Path | Role |
|------|------|
| `v2/` | Production application |
| `data/` | Product data (mostly gitignored runtime content) |
| `tools/investigation/` | Active offline utilities (partially broken on `LEGACY_RP_APP`) |
| `tools/maintenance/` | Issue 86/88 utilities |
| `docs/`, root PRD/architecture docs | Current documentation |
| `governance/policies/`, active `governance/rp-app/v2-*.md` (non-retirement) | Current governance authorities |

### Anomalies

- **`governance/archive/validation-runs/`** contains runnable Python replay scripts and JSON experiment payloads — largest removable bulk (~81 files).
- **Investigation scripts (~30)** still reference `LEGACY_RP_APP` (`autogen_rp/python/rp_app`) which **does not exist** — transitional broken state, not fresh-start clean.
- **`v2/domain/tests/Testing TODOs/`** still references `autogen_rp/python` paths.

---

## 5. Active compatibility inventory

| Artifact | Location | Purpose | Safe to remove now? | Prerequisite |
|----------|----------|---------|---------------------|--------------|
| `legacy_data_dir()` | `v2/domain/paths.py` | Compute migration source path | **No** | Confirm operator + CI data migrated |
| `autogen_python_data_dir()` | `v2/domain/paths.py` | Deprecated alias | **Yes** (after migration sunset) | Remove callers first |
| `ensure_data_migrated()` / `run_data_migration()` | `paths.py`, `data_migration.py` | Auto-copy legacy → `data/` | **No** | Migration check command + marker audit |
| `MIGRATION_MARKER_NAME` | `.hg_data_migration_v1.json` | Idempotent migration guard | **No** | Same |
| `LEGACY_RP_APP` | `tools/_repo_paths.py` | Investigation import path | **Partial** — path is dead | Rewrite or delete dependent scripts |
| `resolve_rp_audits_dir()` legacy fallback | `tools/_repo_paths.py` | Old audit location | **Maybe** | Confirm audits only under `data/rp_audits` |
| `.gitignore autogen_rp/` | root | Privacy for local legacy tree | **After migration** | Operator acknowledges local cleanup |
| `Launch-Holy-Grail-V2.bat` | root | Launcher | **Rename only** | Product naming slice |
| `legacy/__init__.py` | root | Namespace marker | **Yes** | No imports found in production |
| M12 scripts | `scripts/` | Historical automation | **Yes** | None for runtime |
| Retirement tests (7 files) | `v2/tests/` | Prove M12/M13 invariants | **After** residue removed | Replace with fresh-start completion test |

**Domain-code `legacy` identifiers** (`REFUSAL_LEGACY_*`, `production_legacy` eval profile) are **in-scene semantics**, not repository V1 residue — **KEEP**.

---

## 6. `v2/` naming assessment

### Current dependency surface

| Consumer | `v2/` coupling |
|----------|----------------|
| `v2/domain/paths.py` | `repo_root()` = parent of `v2/` |
| `Launch-Holy-Grail-V2.bat` | `cd v2\rp_runtime` |
| `pyproject.toml` | Documents V2; pytest paths in docs/commands |
| `v2/rp_runtime/cordis.yml`, npm scripts | Internal relative paths |
| `governance/rp-app/*.md` | Hundreds of path references |
| `docs/testing.md`, `README.md` | Test commands use `v2/...` |
| CI / operator habit | Established commands |

### Rename/re-home impact

- **High churn:** ~300 tracked files under `v2/`, plus docs, governance, launcher, path helpers.
- **External risk:** Low (single-repo operator workflow); no published package path dependency on `v2` name.
- **Semantic value today:** `v2` no longer marks an coexistence boundary — it **is** the product. The name is now **transitional residue** relative to fresh-start goals.

### Recommendation

| Option | Verdict |
|--------|---------|
| **Retain `v2/` short term** | Lowest risk; acceptable if docs drop "V2 vs V1" framing |
| **Promote to neutral roots** (`domain/`, `rp_runtime/`, `ui/` at repo root or under `app/`) | Aligns with fresh-start; **defer to dedicated slice** after archive/compat cleanup |
| **Rename launcher only** (`Launch-Holy-Grail.bat`) | Low-cost hygiene; do with doc rewrite slice |

**Do not block other cleanup on `v2/` rename.** Treat as optional **M14.x** slice with explicit path migration plan.

---

## 7. Governance and archive reassessment

Under fresh-start goal, prior "preserve evidence in tree" decisions are **reopened**.

| Class | Examples | Fresh-start disposition |
|-------|----------|-------------------------|
| **A — Required durable authority** | `governance/policies/`, active `v2-dsh-replatforming-authority.md`, `issue-tracking-workflow.md`, `failure-taxonomy-spec-v1.md` | **KEEP** (consider dropping `v1` from filenames later) |
| **B — Optional historical evidence** | `governance/archive/validation-runs/` | **DELETE from tree** — git history + GitHub issues retain traceability |
| **C — Obsolete implementation history** | `scripts/m12_*`, `legacy/__init__.py`, V1 replay scripts in archive | **DELETE** |
| **D — Superseded V1 evidence** | `governance/archive/v1-runtime/`, investigation-audits, RP_SETUP_TODO | **DELETE** |
| **E — Traceability records** | M12/M13 `governance/rp-app/v2-repository-retirement-*`, `v2-v1-*` | **OPTIONAL KEEP** in `governance/` or **DELETE** if git history deemed sufficient |

**Estimate removable without impairing current development:** **~110 tracked files** (archive subtrees + M12 scripts + tombstone + retirement tests after replacement).

**Retain in working tree only if:** active governance still cites them by path for ongoing workflow (issue bootstrap profiles reference retirement docs today — rewrite citations if deleted).

---

## 8. Git-history distinction

| Material | After tree deletion |
|----------|---------------------|
| M12/M13 governance, validation JSON, V1 docs | Recoverable via `git log` / GitHub |
| Local ignored `autogen_rp/` | **Not in git** — operator must delete locally for disk cleanliness |
| Migration marker `data/.hg_data_migration_v1.json` | Local/operator data — separate from git |

**History rewriting:** **Not required** for practical fresh-start goal. Deleting tracked residue + rewriting active docs achieves operator intent. Rewriting git history would add risk without proportional benefit.

---

## 9. Retirement test and fixture assessment

| Test file | Role | After fresh-start cleanup |
|-----------|------|---------------------------|
| `test_data_migration_m13_1.py` | Migration behavior | **DELETE** if migration removed |
| `test_autogen_rp_container_retirement_m13_7.py` | No tracked container | **DELETE** — superseded by completion test |
| `test_investigation_tooling_m13_6.py` | Scripts not in old path | **DELETE** or fold into tooling smoke |
| `test_validation_runs_archive_m13_5.py` | Archive integrity | **DELETE** if archive deleted |
| `test_m12_4_orchestration_deletion.py` | `rp_app` absent | **DELETE** |
| `test_m12_5_autogen_removal.py` | No AutoGen imports | **KEEP** or merge into domain import guard |
| `test_character_cards_m12_1.py`, `test_domain_library_m12_2.py` | Feature tests (M12 milestone name only) | **KEEP** — rename optional |

**New completion test (future):** single `test_fresh_start_repository_invariants.py` asserting allowlisted legacy terms only in explicit fixture/governance paths (if any remain).

---

## 10. Documentation assessment

| Doc | Class | Fresh-start action |
|-----|-------|-------------------|
| `README.md` | Canonical but V1-relative framing | **REWRITE** — Holy Grail RP as primary; remove V1 archive pointers from hero |
| `ARCHITECTURE_OVERVIEW.md` | Canonical | **REWRITE** — lead with current stack; demote M12.4 banner |
| `MODULE_INDEX.md` | Canonical | **REWRITE** — remove `autogen_rp/python/rp_app` historical column |
| `docs/architecture.md`, `rp-data-layout.md`, `audit-workflows.md` | Canonical | **REWRITE** legacy path tables |
| `AGENTS.md` | Canonical | **REWRITE** — remove `autogen_rp` routing |
| `CHECKPOINT_BASELINE_DSH.md` | Canonical onboarding | **REWRITE** V1 references |
| `governance/rp-app/v2-*.md` (feature authorities) | Current governance | **KEEP** — filenames may retain `v2` prefix |
| M12/M13 retirement records | Historical | **DELETE or archive-off-tree** per operator preference |
| `governance/archive/*` READMEs | Historical | **DELETE with archive** |

**Target voice:** explain what Holy Grail RP **is**, not how it differs from retired V1.

---

## 11. Migration compatibility assessment

| Question | Finding |
|----------|---------|
| Repository-managed data still needs migration? | **No** — tracked fixtures/templates already under `data/` |
| Migration for unknown operator installs? | **Yes** — `data_migration.py` supports local `autogen_rp/python/data` |
| This operator migrated? | **Uncertain** — local ignored `autogen_rp/` still exists (~68k files); canonical `data/` also populated |
| Evidence before deleting compat | (1) `data/.hg_data_migration_v1.json` present or legacy tree empty; (2) explicit `hg-data-migrate --check` style command; (3) operator confirmation |
| Safe retirement path | Ship **final migration/check command** → document one-time run → remove auto-migration from `paths.py` hot path → delete `legacy_data_dir()` |

**`legacy_data_dir()` is not architectural dependence** — it is **operator-local migration compatibility**. Removable after explicit check.

---

## 12. Proposed fresh-start repository tree

```text
Holy-Grail-RP-DeepSeek-Harness/
├── .venv/                          # local ignored
├── AGENTS.md
├── ARCHITECTURE_OVERVIEW.md
├── data/                           # HG_DATA_DIR (fixtures/templates tracked)
├── docs/
├── governance/
│   ├── policies/                   # current authorities
│   └── rp-app/                     # current feature governance (v2-* filenames OK)
├── tools/
│   ├── investigation/              # rp_app-free scripts only
│   └── maintenance/
├── v2/                             # OPTIONAL later: promote/rename
│   ├── domain/
│   ├── domain_api/
│   ├── rp_runtime/
│   ├── ui/
│   └── tests/
├── Launch-Holy-Grail.bat           # renamed from V2 launcher
├── pyproject.toml
└── README.md
```

**Explicitly absent in target tree:**

- `autogen_rp/` (tracked or documented as architecture)
- `governance/archive/v1-runtime/`
- `governance/archive/validation-runs/` (bulk evidence)
- `scripts/m12_*`
- `legacy/`
- Auto-migration on every data path access
- Retirement-program proof tests (replaced by one completion test)

**May remain temporarily:**

- `v2/` directory name (until promotion slice)
- `governance/rp-app/v2-*` authority docs (filename prefix low harm)
- Git history (always)

---

## 13. Deletion / rewrite matrix (summary)

| Item / class | Current purpose | Disposition | Risk | Prerequisite | Slice |
|--------------|-----------------|-------------|------|--------------|-------|
| `governance/archive/v1-runtime/` | V1 docs | **DELETE** | Low | None | M14.1 |
| `governance/archive/validation-runs/` | Experiment evidence | **DELETE** | Low–med | Confirm no active script deps | M14.1 |
| `governance/archive/investigation-audits/` | Old audits | **DELETE** | Low | None | M14.1 |
| `governance/archive/planning/` | Setup todo | **DELETE** | Low | None | M14.1 |
| `governance/archives/issue-215/` | Adjudication history | **DELETE** or **OPTIONAL** | Low | Issue workflow cites? | M14.1 |
| `scripts/m12_*.py` | One-shot migration | **DELETE** | Low | None | M14.1 |
| `legacy/__init__.py` | Tombstone | **DELETE** | Low | Grep imports | M14.1 |
| `data_migration.py` + hot-path hooks | Auto migration | **DELETE AFTER MIGRATION CHECK** | Med | Migration command + operator sign-off | M14.2 |
| `legacy_data_dir()`, `.gitignore autogen_rp/` | Legacy path | **DELETE AFTER MIGRATION CHECK** | Med | M14.2 complete | M14.2 |
| `LEGACY_RP_APP` + broken investigation scripts | rp_app imports | **REWRITE or DELETE** | Med | Classify per-script utility | M14.3 |
| Retirement tests (`test_m12_*`, `test_m13_*`) | Program proofs | **DELETE** | Low | Fresh-start completion test added | M14.3 |
| `README.md`, `ARCHITECTURE_*`, `docs/*` | User-facing docs | **REWRITE** | Low | M14.1–3 done | M14.4 |
| `Launch-Holy-Grail-V2.bat` | Launcher | **RENAME** | Low | Doc update | M14.4 |
| `v2/` top-level directory | Product root | **INVESTIGATE FURTHER** | **High** | Dedicated path migration plan | M14.5 (optional) |
| `governance/rp-app/v2-repository-retirement-m13*` | Program record | **HISTORICAL ONLY** | Low | Operator choice | M14.1 or keep |
| Domain `REFUSAL_LEGACY_*` | Dialogue logic | **KEEP** | — | — | — |
| `test_m12_5_autogen_removal.py` | Import guard | **KEEP** | — | — | — |

---

## 14. Recommended bounded implementation sequence

### M14.1 — Archive and tombstone purge

- **Objective:** Remove tracked historical implementation/evidence trees superseded by git history.
- **Scope:** Delete `governance/archive/**` (or agreed subset), `governance/archives/**`, `scripts/m12_*`, `legacy/__init__.py`; update `AGENTS.md` / bootstrap doc links.
- **Risk:** Low — no runtime import of archive content.
- **Validation:** Full pytest + npm suites; `git grep governance/archive` only in historical governance if retained.
- **Dependency:** None.

### M14.2 — Migration compatibility sunset

- **Objective:** Replace implicit auto-migration with explicit one-shot check; remove `legacy_data_dir()` chain.
- **Scope:** `data_migration.py`, `ensure_data_migrated()` calls in `paths.py`, `.gitignore autogen_rp/` policy decision, migration tests.
- **Risk:** Medium — operator data loss if migrated incorrectly.
- **Validation:** New migration check command; `test_data_migration` replaced by check-only tests; manual verify on operator workstation.
- **Dependency:** M14.1 optional first.

### M14.3 — Investigation tooling and retirement-test cleanup

- **Objective:** Remove or repair `LEGACY_RP_APP` scripts; delete M12/M13 proof tests; add `test_fresh_start_repository_invariants.py`.
- **Scope:** `tools/investigation/*`, `tools/_repo_paths.py`, `v2/tests/test_m12_*`, `test_m13_*`, `test_autogen_rp_*`.
- **Risk:** Medium — script usefulness loss.
- **Validation:** Remaining investigation README documents working scripts; full test suites.
- **Dependency:** M14.2 if scripts assume legacy data paths.

### M14.4 — Documentation and launcher fresh-start rewrite

- **Objective:** Current-state documentation; product naming without V1 contrast.
- **Scope:** `README.md`, `ARCHITECTURE_OVERVIEW.md`, `MODULE_INDEX.md`, `docs/*`, rename launcher.
- **Risk:** Low.
- **Validation:** Doc review checklist; no `autogen_rp` in active docs except allowlist.
- **Dependency:** M14.1–3.

### M14.5 — Optional `v2/` promotion (Governance-gated)

- **Objective:** Rename `v2/` → neutral application root if approved.
- **Scope:** Mass path update.
- **Risk:** High churn.
- **Validation:** Full suites + supervisor smoke.
- **Dependency:** M14.4 recommended first.

---

## 15. Objective fresh-start completion criteria

Repository-wide **done** when:

1. `git ls-files` contains **no** `governance/archive/v1-runtime`, `governance/archive/validation-runs`, `scripts/m12_*`, or `legacy/`.
2. **No** production code computes `autogen_rp/` paths (migration module removed).
3. **No** active documentation presents V1/AutoGen/`autogen_rp` as current architecture.
4. `git grep -l autogen_rp` on tracked files returns **only** an explicit allowlist (if any — target **zero**).
5. `git grep -l rp_app` on tracked **Python/JS production paths** returns **zero**.
6. Investigation tooling either works without `LEGACY_RP_APP` or is removed.
7. `python -m pytest v2/domain/tests/ -q` → **358 passed** (or current baseline).
8. `python -m pytest v2/tests/ -q` → integration baseline green (xfail descriptive-exit may remain).
9. `cd v2/rp_runtime && npm test` → **70 passed**.
10. Single fresh-start invariant test documents any intentional exceptions.

---

## 16. Validation baseline (investigation pass)

| Suite | Result |
|-------|--------|
| `python -m pytest v2/domain/tests/ -q` | **358 passed** |
| `python -m pytest v2/tests/ -q` | **160 passed, 1 xfailed** |
| `cd v2/rp_runtime && npm test` | **70 passed** |

No unrelated failures observed.

---

## 17. Unresolved risks and questions

1. **Operator local `autogen_rp/` (~68k files)** — Has canonical `data/` superseded it? Need explicit migration audit before M14.2.
2. **Investigation script value** — Which `LEGACY_RP_APP` scripts are still worth porting vs deleting?
3. **Issue bootstrap profiles** — Do they **require** M13 governance paths on disk, or can they cite git history / condensed authority?
4. **`governance/archives/issue-215/`** — Any open issue workflow dependency?
5. **`v2/` rename** — Operator appetite for high-churn path promotion vs doc-only fresh-start.
6. **Fixture `*_v1.json` naming** — Keep as artifact labels (recommended) vs rename for cosmetic consistency.

---

## 18. Architecture verdict

**M13 repository retirement is complete for production architecture.**  
**M14 fresh-start residue removal is NOT complete** — substantial tracked historical material, migration compatibility, broken investigation paths, and V1-relative documentation remain.

**Verdict:** `fresh-start requires bounded M14 implementation — archive purge, migration sunset, tooling cleanup, doc rewrite`

---

## 19. Repository state

| Field | Value |
|-------|-------|
| Investigation record commit | d5bb1a4942ee40e04088d02a4874d5d842fa6bf4 |
| Pre-investigation HEAD | `9e2592c` |
| Branch | `main` |
| Working tree at investigation | clean |

---

## 20. Recommended first implementation slice

**M14.1 — Archive and tombstone purge**

Lowest risk, highest visible cleanliness gain (~110 files), no product behavior change, validates fresh-start direction before migration sunset.

**Do not implement without Governance review of this investigation record.**
