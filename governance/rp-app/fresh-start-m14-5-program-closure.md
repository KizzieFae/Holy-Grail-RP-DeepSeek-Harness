# M14 Fresh-Start Program Closure

**Status:** Complete  
**Date:** 2026-08-18  
**Program:** M14 Fresh-Start Repository  
**M14.5 implementation HEAD:** `ac5c0a34784202f99f9581b1644a6facf47297cc`

**Assigned workflow weight:** standard  
**Effective workflow weight:** full

---

## 1. Activation

| Field | Value |
|-------|-------|
| Pre-slice HEAD | `2157732` (M14.4) |
| Branch | `main` |

---

## 2. Local autogen_rp re-verification

| Check | Result |
|-------|--------|
| `hg_data_migration_check.py --check` | `compatibility_retirement_safe: True` |
| Legacy sessions | 1450 ids; **0** missing in canonical |
| Legacy-only rp_audits | 82 (historical; not production) |
| Cross-scope / scope knowledge | **0** unique legacy files |
| Active tooling/docs dependency | **0** |

---

## 3. Local autogen_rp deletion

Operator-authorized deletion of `autogen_rp/` (~68k files) completed. Path verified absent.

---

## 4. `.gitignore` cleanup

Removed `autogen_rp/` blanket ignore rule. Retained unrelated privacy/data rules.

---

## 5. Migration-check tool

**Deleted:** `tools/maintenance/hg_data_migration_check.py` — no remaining migration source.

---

## 6–9. Governance purge

**Retained (current authority):**

- `issue-tracking-workflow.md`
- `workflow-weights.md`
- `audit-classification-protocol.md`
- `failure-taxonomy-spec-v1.md`
- `round-a-strata-grid-v0.md`
- `round-a-serialized-exemplar-export-checklist-v0.md`

**Deleted:** all M12/M13/M14 execution records, V2 slice implementation reports, `fresh-start-m14-1` through `m14-4`, `fresh-start-residue-investigation-m14.md`, and obsolete `CHECKPOINT_BASELINE_DSH.md`.

Authority already captured in: `README.md`, `ARCHITECTURE_OVERVIEW.md`, `AGENTS.md`, `docs/`, `v2/tests/test_repository_architecture.py`.

---

## 10. Launcher

**Renamed:** `Launch-Holy-Grail-V2.bat` → `Launch-Holy-Grail-RP.bat` (same behavior).

---

## 11. `v2/` root

**KEEP** — stable implementation namespace; rename churn not justified.

---

## 12. Architecture invariant updates

`test_repository_architecture.py`:

- `test_local_autogen_rp_tree_absent`
- `test_gitignore_does_not_hide_legacy_autogen_rp`
- `test_no_legacy_migration_check_tool`

---

## 13. Validation

| Suite | Result |
|-------|--------|
| `v2/domain/tests` | 358 passed |
| `v2/tests` | 136 passed, 1 xfail |
| `v2/rp_runtime npm test` | 70 passed |

---

## 14. M14 completion verdict

**Fresh-start objective fully achieved** with intentional literal implementation-name exceptions: `v2/` path and domain module names such as `turn_runner_*`.

---

## 15. Terminology allowlist (post-closeout)

| Term | Justification |
|------|----------------|
| `v2/` | Literal implementation root |
| `turn_runner_*` | Current domain module names |
| `legacy` | Legitimate domain semantics where applicable |
| `governance/archive/` | Untracked local historical artifacts only (not in git) |

---

## 16. Next phase

M14 closed. Resume normal product development under current authorities only.
