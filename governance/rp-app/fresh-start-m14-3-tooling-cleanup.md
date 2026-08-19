# Fresh-Start M14.3 — Legacy Investigation Tooling + Retirement-Test Cleanup

**Status:** Complete  
**Date:** 2026-08-18  
**M14 investigation anchor:** `d32664a`  
**M14.1 anchor:** `6f17286`  
**M14.2 anchor:** `3bb79dd`  
**Pre-slice HEAD:** `3bb79dd`  
**M14.3 implementation HEAD:** _(set at commit)_

**Assigned workflow weight:** standard  
**Effective workflow weight:** full

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `3bb79dd` |
| Working tree | clean at activation |
| Validation baseline (pre-slice) | domain 358; integration 147 + 1 xfail; rp_runtime 70 |

---

## 2. Pre-M14.3 tooling inventory

| Area | Count | Notes |
|------|-------|-------|
| `tools/investigation/*.py` | 42 | 40 scripts + `_repo_paths.py` re-export + `tools/_repo_paths.py` consumer surface |
| `tools/maintenance/*.py` | 4 | issue86/88 hygiene + `hg_data_migration_check.py` |
| `LEGACY_RP_APP` consumers | 30+ scripts | V1 `rp_app` import path hacks |
| Retirement integration tests | 5 files | M12/M13/M14.2 milestone proofs |

---

## 3. Investigation-script classification

| Class | Count | Action |
|-------|-------|--------|
| **DELETE** | 30 | V1 headless LLM runners, `rp_app` importers, deleted-archive dependents |
| **REPAIR** | 10 | Issue #240 audit readers + comparators/aggregators → current `data/` paths |
| **KEEP** | 1 | `_repo_paths.py` re-export shim |
| **DEFER** | 0 | V2 headless scenario harness (product slice, not M14.3) |

### Deleted (30)

All former V1 runtime / `run_scene_simulation_llm.py` dependents and `rp_app` import probes:

`run_scene_simulation_llm.py`, `run_progression_layer_simulation.py`, `run_participation_adjudication.py`, `build_semantic_eval_baseline.py`, `build_issue246_corpus.py`, `run_issue243_corpus_regression.py`, `run_issue246_corpus_regression.py`, `run_issue246_prior_suite_validation.py`, `compile_authored_retrieval_index.py`, `run_audit_fact_track.py`, `run_presence_scene_audit.py`, `analyze_issue29_run.py`, `analyze_issue29_session.py`, `run_issue29_suite.py`, `extract_cohesion_slate.py`, `extract_emission_map.py`, `extract_willow_departure_experiment.py`, `extract_participation_suspicions.py`, `issue1_analyze_probe_windows.py`, `issue1_run_batch.py`, `run_issue242_baseline_matrix.py`, `run_issue230_stepb_validation.py`, `run_arch_quality_round2_batch.py`, `run_cohesion_slate_batch.py`, `run_override_quality_batch.py`, `run_operational_pilot_eval_matrix.py`, `run_progression_stress_audit_replay.py`, `_issue242_baseline_synthesis.py`, `_issue242_topology_rollup.py`, `_issue240_extract_prompts.py`.

### Repaired / retained (11 scripts)

| Script | Purpose |
|--------|---------|
| `compare_cohesion_slate.py` | Baseline vs treatment JSON comparison |
| `compare_participation_calibration_ab.py` | Participation calibration A/B aggregates |
| `compare_willow_departure_experiment.py` | Willow departure experiment comparison |
| `aggregate_arch_quality_r2.py` | Architecture quality round-2 rollup |
| `_aggregate_r2_report.py` | Shared R2 report helper |
| `audit_episodic_issue_mismatch_scan.py` | Read-only episodic:issue audit scan |
| `_issue240_audit_classifier.py` | Issue #240 audit classifier |
| `_issue240_corrected_scorer.py` | Issue #240 corrected scorer |
| `_issue240_failure_map.py` | Issue #240 failure map |
| `_issue240_build_adjudication_corpus.py` | Issue #240 adjudication corpus builder |
| `_issue240_build_final_adjudication_corpus.py` | Issue #240 final adjudication corpus |

Repairs: `resolve_rp_audits_dir()` / `FIXTURES_DIR` for canonical paths; removed `LEGACY_RP_APP` / legacy audit fallbacks.

---

## 4. Maintenance-tool classification

| Script | Class | Decision |
|--------|-------|----------|
| `hg_data_migration_check.py` | **KEEP** | Operator legacy-vs-canonical check (M14.2); legitimately references local `autogen_rp/python/data` |
| `issue86_inventory_pass.py` | **KEEP** | Current `rp_audits` inventory hygiene |
| `issue88_tranche1_prepare.py` | **KEEP** | Registry snapshot prep |
| `issue88_tranche2_duplicate_plan.py` | **KEEP** | Duplicate equivalence plan |

---

## 5. `LEGACY_RP_APP` / `_repo_paths` cleanup

| Item | Result |
|------|--------|
| `LEGACY_RP_APP` | **Removed** from `tools/_repo_paths.py` |
| Legacy audit fallback in `resolve_rp_audits_dir()` | **Removed** — returns `DATA_DIR / "rp_audits"` only |
| Retired archive aliases | **Removed** |
| Retained helpers | `REPO_ROOT`, `DATA_DIR`, `FIXTURES_DIR`, `INVESTIGATION_RUNS_DIR`, `resolve_rp_audits_dir()`, `fixture_path()`, `resolve_data_path()` |

---

## 6. Retirement-test inventory

| File | Class | Action |
|------|-------|--------|
| `test_m12_4_orchestration_deletion.py` | One-time retirement proof | **Deleted** |
| `test_m12_5_autogen_removal.py` | One-time retirement proof | **Deleted** |
| `test_investigation_tooling_m13_6.py` | One-time move proof | **Deleted** |
| `test_autogen_rp_container_retirement_m13_7.py` | One-time container proof | **Deleted** |
| `test_canonical_data_paths_m14_2.py` | Duplicate of consolidated invariants | **Deleted** |
| `test_domain_library_m12_2.py` | Permanent feature coverage | **Kept** |
| `test_character_cards_m12_1.py` | Permanent feature coverage | **Kept** |
| `test_retrieval_index_m12_7.py` | Permanent feature coverage | **Kept** |
| `test_opening_bootstrap_m12_6.py` | Permanent feature coverage | **Kept** |
| `test_player_settings_m12_8.py` | Permanent feature coverage | **Kept** |

---

## 7. Permanent architecture invariant

**Added:** `v2/tests/test_repository_architecture.py` (10 tests)

Covers:

- No tracked `autogen_rp` files
- Root `.gitignore` covers operator-local `autogen_rp/`
- Canonical `paths.py` (no migration hooks)
- `HG_DATA_DIR` / `HG_SESSIONS_DIR` overrides
- No AutoGen imports in `v2/domain` + `v2/domain_api`
- No legacy orchestration tokens in production Python
- Framework-neutral `v2/domain/modules`
- Active tooling free of `LEGACY_RP_APP` / `rp_app` path hacks
- Investigation tooling presence + comparator `--help` smoke

---

## 8. Tool documentation

| File | Change |
|------|--------|
| `tools/investigation/README.md` | Rewritten for 11 retained scripts only |
| `tools/maintenance/README.md` | Added `hg_data_migration_check.py` |
| `MODULE_INDEX.md` | Bounded removal of deleted `run_scene_simulation_llm.py` references |

---

## 9. Terminology audit (active tooling/tests/production)

| Token | Active residue |
|-------|----------------|
| `rp_app` | **0** in `tools/`; only forbidden-token assertions in `test_repository_architecture.py` |
| `turn_runner` | **0** in tools; forbidden-token guard in architecture test |
| `LEGACY_RP_APP` | **0** (removed) |
| `autogen_rp` | **1** maintenance script (`hg_data_migration_check.py`) — intentional operator check |
| `AutoGen` | **0** production imports; anti-import invariant test retained |

---

## 10. Local `autogen_rp` tooling dependency

| Check | Result |
|-------|--------|
| Active investigation scripts reading local `autogen_rp/` | **0** |
| Active maintenance (except migration check) | **0** |
| Production `v2/` paths | **0** (M14.2) |

Operator-local tree remains safe to delete for runtime; `.gitignore autogen_rp/` retained while tree exists.

---

## 11. Product-behavior guardrail

**No changes** to Domain Host, DSH orchestration, continuity, memory, KnowledgeService, retrieval, opening, player/settings, data paths, session persistence, or UI.

---

## 12. Validation

| Suite | Pre-M14.3 | Post-M14.3 |
|-------|-----------|------------|
| `v2/domain/tests` | 358 passed | **358 passed** |
| `v2/tests` | 147 passed, 1 xfail | **133 passed, 1 xfail** (−14 net: −24 retirement, +10 architecture) |
| `v2/rp_runtime npm test` | 70 passed | **70 passed** |

Focused tooling: `--help` on all retained investigation scripts (including `audit_episodic_issue_mismatch_scan.py` after argparse fix).

---

## 13. Challenge / refinement

- Deleted scripts lacked current value (V1-only) rather than age alone.
- Retained comparators and Issue #240 audit readers still diagnose real audit JSON.
- Did not repair V1 headless runners — deleted instead of recreating compatibility.
- Consolidated milestone tests into semantic `test_repository_architecture.py`.
- Framework independence and canonical data paths still guarded.
- M14.4 remains primarily documentation / V1-relative language cleanup (`SCENARIO_VALIDATION_FRAMEWORK.md`, `docs/architecture.md`, governance historical notes).

---

## 14. Architecture verdict

**Tooling/test cleanup complete.**

---

## 15. M14.4 readiness

Remaining old-version references are primarily documentation and governance language. Active application code, tooling, and tests present a current Holy Grail architecture.

**Next slice:** M14.4 — Current documentation fresh-start rewrite + product naming cleanup.
