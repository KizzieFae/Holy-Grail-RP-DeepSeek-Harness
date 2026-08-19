# V2 Repository Retirement — M13.5 Validation Evidence Archive Rehome

**Status:** Complete  
**Date:** 2026-08-18  
**M13.4 anchor:** `1927b5c`  
**M13.5 implementation HEAD:** `a158227`

**Objective:** Rehome historical validation evidence from `autogen_rp/python/validation_runs/` to `governance/archive/validation-runs/` without rewriting historical records or altering product behavior.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `1927b5c` |
| Working tree | clean at activation |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 repository-hygiene implementation |

**Pre-move validation baseline:**

| Suite | Result |
|-------|--------|
| `v2/domain/tests` | 358 passed |
| `v2/tests` | 146 passed, 1 xfailed (descriptive-exit; out of scope) |
| `v2/rp_runtime npm test` | 70 passed |

---

## 2. Pre-M13.5 validation-runs inventory

**Source:** `autogen_rp/python/validation_runs/` — **81 tracked files**

| Type | Count | Role |
|------|-------|------|
| Markdown reports | 41 | Issue investigations, synthesis, adjudication packets |
| Python | 15 | Historical runners/helpers (issue251, plan_execution, progression_stress_batch) |
| JSONL | 15 | Cohesion/willow/M3 experiment extracts |
| JSON | 10 | plan_execution structured_eval snapshots, issue249 results |

**Major subtrees:**

| Path | Semantic role |
|------|---------------|
| `issue230_stepB/` | #230 Step B harmonization evidence |
| `issue242_*` | #242 participation/emission waves (baseline, wave0–3, final) |
| `issue249/` | #249 proposal-schema experiment plans + results |
| `issue251/` | #251 physical-severance doctrine investigations |
| `plan_execution/` | Post–#24 headless structured_eval JSON + analyzer |
| `cohesion_slate/` | #227 cohesion JSONL arms |
| `participation_adjudication/` | #246 prior-suite reports |
| `progression_stress_batch/` | Historical batch runner |
| Root `*.md`, `*.jsonl` | Cross-issue synthesis (willow departure, M3, manual adjudication) |

---

## 3. Evidence vs active-tool classification

| Path pattern | Executable? | Active consumer? | Historical evidence? | Disposition |
|--------------|-------------|------------------|----------------------|-------------|
| `*.md`, `*.json`, `*.jsonl` (reports/snapshots) | No | Docs/scripts read-only | **Yes** | **Archive** |
| `issue251/run_*.py`, `i251_*.py` (except alignment) | Yes (historical) | No production import | **Yes** | **Archive** (repro scripts as evidence) |
| `issue251/i251_doctrine_alignment.py` | Yes | `v2/domain/tests/test_i251_doctrine_alignment.py` | Partial | **Extract to test fixture** |
| `plan_execution/analyze_validation_audits.py` | Yes | No active CI | **Yes** | **Archive** |
| `progression_stress_batch/run_batch.py` | Yes | No active CI | **Yes** | **Archive** |
| `autogen_rp/python/scripts/*.py` (8 readers) | Yes | Investigation tooling | N/A | **Retain** — updated to `_archive_paths.py` |

**Boundary verdict:** One active domain-test dependency (`i251_doctrine_alignment.py`) extracted; governance archive is not a production/test import API.

---

## 4. Final archive location/structure

```
governance/archive/validation-runs/
  README.md
  issue230_stepB/
  issue242_baseline/
  issue242_final/
  issue242_wave0/
  issue242_wave1/
  issue242_wave2/
  issue242_wave3/
  issue249/
  issue251/
  plan_execution/
  cohesion_slate/
  participation_adjudication/
  progression_stress_batch/
  *.md, *.jsonl (root synthesis)
```

Aligns with `governance/archive/v1-runtime/` — sibling immutable evidence trees under `governance/archive/`.

---

## 5. Evidence moved

**80 files** `git mv` from `autogen_rp/python/validation_runs/` → `governance/archive/validation-runs/` preserving issue-organized hierarchy.

---

## 6. Files intentionally retained outside archive

| Path | Reason |
|------|--------|
| `v2/domain/tests/fixtures/issue251/i251_doctrine_alignment.py` | Permanent domain test fixture (extracted from archive candidate tree) |
| `autogen_rp/python/scripts/_archive_paths.py` | Shared `VALIDATION_RUNS_ARCHIVE` helper for investigation scripts |
| `autogen_rp/python/scripts/` (8 updated readers) | Active investigation tooling — not evidence |

---

## 7. Files deleted as obsolete residue

**None.** All 81 tracked source files preserved (80 archived + 1 fixture-extracted). No empty duplicates or generic upstream-only noise identified for deletion.

---

## 8. Archive provenance/indexing

- `governance/archive/validation-runs/README.md` — source path, M13.5 migration, current architecture map, historical-content policy, mutability policy, fixture split note.
- `v2/tests/test_validation_runs_archive_m13_5.py` — integrity tests (archive exists, legacy path removed, evidence count, fixture extracted, plan_execution present).

**Mutability policy:** New validation output must not be written to the archive; treat contents as read-only historical evidence.

---

## 9. Active-reference migration

| Target | Change |
|--------|--------|
| 8 investigation scripts | Import `VALIDATION_RUNS_ARCHIVE` from `_archive_paths.py` |
| `v2/domain/tests/test_i251_doctrine_alignment.py` | Import from `fixtures/issue251/` |
| `README.md`, `ARCHITECTURE_OVERVIEW.md`, `PACKET_CONTRACTS.md`, `SCENARIO_VALIDATION_FRAMEWORK.md`, `MODULE_INDEX.md`, `autogen_rp/python/README.md`, `autogen_rp/python/RP_SETUP_TODO.md` | Point to `governance/archive/validation-runs/` |
| `.gitignore` | Generated-artifact ignore patterns relocated to archive path |

**Not modified:** Historical governance records (M13.1–M13.4), archived evidence body text, `governance/archive/v1-runtime/*`.

---

## 10. Test-fixture treatment

`i251_doctrine_alignment.py` → `v2/domain/tests/fixtures/issue251/i251_doctrine_alignment.py`

Rationale: sole active production-adjacent import; pure evaluation helper with no archive coupling. Tests no longer depend on governance archive layout.

---

## 11. Reproducibility-script treatment

Issue-specific `run_*.py` and helpers co-located in archive remain as **historical reproduction source text**. Not promoted to active tooling. Investigation scripts that aggregate archived JSONL remain under `autogen_rp/python/scripts/`.

---

## 12. Historical-content preservation

Archived markdown/JSON retain original `autogen_rp/python/validation_runs/` path strings, commit references, command lines, and timestamps. No bulk path rewrite inside evidence files.

---

## 13. Active documentation updates

See §9. Console-capture guidance in `SCENARIO_VALIDATION_FRAMEWORK.md` now directs readers to archive README for historical evidence.

---

## 14. Archive integrity proof

| Check | Result |
|-------|--------|
| `governance/archive/validation-runs/` exists | **Yes** |
| 80 tracked evidence files + README | **Yes** |
| `autogen_rp/python/validation_runs/` removed | **Yes** |
| `plan_execution/*.json` (≥5) in archive | **Yes** |
| No production import of archive | **Yes** |
| `test_validation_runs_archive_m13_5.py` | **6 passed** |

---

## 15. Full behavioral validation

| Suite | Post-M13.5 result |
|-------|-------------------|
| `python -m pytest v2/domain/tests/ -q` | **358 passed** |
| `python -m pytest v2/tests/ -q` | **152 passed**, 1 xfailed |
| `cd v2/rp_runtime && npm test` | **70 passed** |

(+6 archive integrity tests in `v2/tests/` vs pre-slice 146 baseline.)

---

## 16. Product-behavior guardrail confirmation

**No changes** to `v2/domain`, `v2/domain_api`, `v2/rp_runtime`, `v2/ui`, data migration, MemoryService, KnowledgeService, continuity, opening, retrieval, or player/settings.

---

## 17. Old-path residue audit

| Match class | Count (active operational) |
|-------------|----------------------------|
| Active `.py`/`.mjs` operational references | **0** |
| Archive README provenance | 1 (intentional) |
| Archive integrity test | 1 (intentional) |
| Historical governance (M13.x, M12.x) | retained unchanged |
| Archived evidence body text | retained unchanged |

---

## 18. Post-M13.5 autogen_rp inventory

**Tracked under `autogen_rp/`:** ~65 files (down from ~145 pre-M13.5)

| Category | Remaining |
|----------|-----------|
| `autogen_rp/python/scripts/` | Investigation/headless tooling |
| `autogen_rp/python/docs/`, `RP_SETUP_TODO.md`, README | Active/historical docs |
| `autogen_rp/python/rp_app/` remnants | Legacy app shell (fenced) |
| `autogen_rp/docs/`, `autogen_rp/tools/` | Container metadata |
| `validation_runs/` | **Removed** |

---

## 19. Clean-V2 assessment

| Layer | Depends on `autogen_rp/python/validation_runs`? |
|-------|-----------------------------------------------|
| Permanent production | **No** |
| Permanent tests | **No** (fixture extracted) |
| Active data (`data/`) | **No** |
| Active tooling | **No** — reads archive via `_archive_paths.py` |
| Historical evidence | **`governance/archive/validation-runs/`** |

> Does any active production or test architecture depend on validation evidence remaining under `autogen_rp`?

**No.**

---

## 20. Challenge/refinement

| Question | Answer |
|----------|--------|
| Evidence vs tooling distinguished? | **Yes** — one fixture extracted; scripts retained |
| Governance archive made active API? | **No** — only investigation scripts read archive |
| Unique Holy Grail records preserved? | **Yes** — 81/81 tracked files accounted |
| Historical paths preserved in evidence? | **Yes** |
| Relative links within subtrees? | **Yes** — hierarchy preserved |
| Dead noise archived unnecessarily? | **No deletions** — conservative preservation |
| New runs prevented in archive? | **Yes** — README + mutability policy |
| Active docs updated? | **Yes** |
| Production code changed without necessity? | **No** |
| `autogen_rp` easier to retire? | **Yes** — largest evidence subtree removed |
| Script cleanup combined? | **No** — path helper only |

**Architecture verdict:** **Validated as designed**

---

## 21. Recommended next bounded slice

**M13.6 — rehome active investigation scripts/docs** from `autogen_rp/python/scripts/` and remaining Holy Grail docs to a neutral tooling path (e.g. `tools/investigation/` or `scripts/legacy-rp/`), with governance review before execution. Do not combine with `autogen_rp` container deletion.

---

## 22. Repository state

| Field | Value |
|-------|-------|
| Implementation commit | `a158227` — `feat(m13.5): archive validation evidence under governance` |
| Branch | `main` |
| Pre-slice HEAD | `1927b5c` |
