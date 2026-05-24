# Participation Calibration A/B Experiment — Implementation Report

**Commit SHA (working tree, uncommitted):** `e230e39526fce266e1023d71b90f412761e28474`  
**Authoritative A/B sessions (harness v3):** baseline `session_897`, calibrated `session_898`  
**Prior partial runs (harness v2, confounded):** baseline `session_894`, calibrated `session_896` (invalid parse gate on 895)

---

## 1. System understanding report

### Proven (carried forward)
- Proposal infrastructure, legality/retry, and Harley control cases work when the model emits.
- Willow/session_890 failure was **emission calibration**, not legality suppression.
- Phase A (session_892, pre-harness-fix) reproduced missed covered-change emissions without `must_remain`, focus capsules, participation arcs, or large-scene complexity.

### Primary ontology gap
`v1_next7` calibrates covered change mainly around **focal conversational participation** and arc-linked gradual withdrawal/rejoin. It under-specifies **physical scene-membership transitions**, nearby/off-focal relocation, remote channels, and transitional exits/reentries — while still needing to preserve doorway continuation, immediate-return beats, and socially tethered edge speech.

### Harness confounds discovered and fixed
| Confound | Root cause | Fix |
|----------|------------|-----|
| Probe text redacted from addressee | Substring `"into "` in probe copy triggered private-speech heuristic in `normalize_move_audibility` | Reword schedule; avoid `"into "` / whisper markers |
| Wrong actor on probe turns | Director pick + offstage after T01 exit | `make_forced_speaker_from_actor_targeted_schedule` + ordering before pre-turn routing |
| Forced speaker not eligible after offstage | `release_pending_forced_speaker` cleared offstage list but not `present_characters` | `ensure_forced_probe_actor_present` → canonical reentry scratch |
| Early session termination | Director `end_round` | `--ignore-end-round` allowed for `investigate_i240_*` scenarios |
| Calibrated variant parse failures | `issue240_semantic_evaluation_enabled()` did not recognize calibration env alias | Register `v1_next7_participation_calibration_a` in semantic eval topologies |

### Experiment design
Isolated env-selectable variant **`v1_next7_participation_calibration_a`** — same stack as `v1_next7` with additional participation-transition ontology, compact examples, lightweight self-check, and rebalanced `no_covered_change` escape hatch. Production default unchanged.

---

## 2. Prompt calibration changes

**File:** `autogen_rp/python/rp_app/prompt_topology_issue240.py`

| Component | Change |
|-----------|--------|
| Env alias | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_calibration_a` |
| Opening | Softens blanket “Honest no_covered_change”; lists legitimate non-covered transitional cases |
| Ontology block | Physical relocation, sub-location, remote channel, local non-presence as *may-be* covered when beats support |
| Examples | Hall exit, workbench, garage phone, immediate-return threshold, doorway continuation |
| Self-check | Lightweight beat-vs-evaluation reconsideration (non-rigid) |
| Builder | `build_character_turn_prompt_issue240_v1_next7_participation_calibration_a` |

**Wire fix:** `autogen_rp/python/rp_app/issue240_semantic_evaluation.py` — calibration alias added to `_SEMANTIC_EVAL_TOPOLOGIES`.

**Diff summary vs `v1_next7`:** ~40 lines added inside semantic block + opening rebalance; no architecture, legality, orchestration, or output-schema changes.

---

## 3. Harness fixes

| File | Change |
|------|--------|
| `data/issue240/i240_emission_probe_schedule_v1.json` | All probes → `by_actor_targeted_turn`; redaction-safe wording |
| `rp_app/user_trigger_schedule.py` | `make_forced_speaker_from_actor_targeted_schedule`, `ensure_forced_probe_actor_present` |
| `rp_app/turn_runner.py` | Forced speaker + reentry before pre-turn presence routing |
| `rp_app/headless_simulation_runner.py` | Pass-through forced-speaker resolver |
| `scripts/run_scene_simulation_llm.py` | Wire forced speaker; allow `--ignore-end-round` for `investigate_i240_*` |
| `scripts/compare_participation_calibration_ab.py` | Side-by-side summary comparison (new) |
| `SCENARIO_VALIDATION_FRAMEWORK.md` | Runbook updated with `--ignore-end-round` |

---

## 4. Baseline vs calibrated rerun summary

### Validation commands (harness v3 — authoritative)

```bash
cd autogen_rp/python

# Baseline (default v1_next7)
python scripts/run_scene_simulation_llm.py \
  --scenario investigate_i240_participation_emission_map \
  --audit --turns 14 --ignore-end-round \
  --user-trigger-schedule data/issue240/i240_emission_probe_schedule_v1.json

python scripts/extract_emission_map.py --audit-session-number 897 \
  --out-jsonl validation_runs/emission_map_baseline_v3.jsonl \
  --out-csv validation_runs/emission_map_baseline_v3.csv \
  --summary-out validation_runs/emission_map_baseline_v3_summary.json

# Calibrated
RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_participation_calibration_a \
python scripts/run_scene_simulation_llm.py \
  --scenario investigate_i240_participation_emission_map \
  --audit --turns 14 --ignore-end-round \
  --user-trigger-schedule data/issue240/i240_emission_probe_schedule_v1.json

python scripts/extract_emission_map.py --audit-session-number 898 \
  --out-jsonl validation_runs/emission_map_calibrated_v3.jsonl \
  --out-csv validation_runs/emission_map_calibrated_v3.csv \
  --summary-out validation_runs/emission_map_calibrated_v3_summary.json

python scripts/compare_participation_calibration_ab.py \
  --baseline-summary validation_runs/emission_map_baseline_v3_summary.json \
  --calibrated-summary validation_runs/emission_map_calibrated_v3_summary.json \
  --out validation_runs/participation_calibration_ab_comparison_v3.json
```

| Metric | Baseline (897) | Calibrated (898) | Δ |
|--------|----------------|------------------|---|
| Continuity turns | 14 | 14 | — |
| Probe overlay hit rate | 8/8 distinct probes, correct actor | 8/8 | — |
| Proposal emission (probe turns) | 0 | 1 | +1 |
| C1 correct no-change | 2 | 2 | 0 |
| C2 correct covered | 0 | 1 | +1 |
| C3 missed covered | 8 | 8 | 0 |
| C4 false positive | 0 | 0 | 0 |
| C5 legality/retry | 0 | 0 | 0 |
| C7 ambiguous | 4 | 3 | −1 |
| C8 fiction denies transition | 3 | 4 | +1 |
| Suspect miss (F_suspect_miss) | 5 | 5 | 0 |

**Per-probe first actor (v3):**

| Probe | Type | Baseline | Calibrated |
|-------|------|----------|------------|
| T01 | clean exit | C3 | C3 |
| T02 | reentry | C3 | C3 |
| T03 | immediate return | C3 | C3 |
| T04 | workbench off-focal | C3 | C3 |
| T05 | remote phone | C3 | **C2** ✓ |
| T07 | present disengaged (control) | **C1** ✓ | **C1** ✓ |
| T09 | passive observer (control) | **C1** ✓ | **C1** ✓ |
| T10 | leave reachable | C3 | C3 |

---

## 5. Emission / false-positive comparison

- **Modest positive signal:** calibrated variant converted **T05 (remote phone)** from C3 → C2 with an honest `covered_change` emission; baseline emitted **zero** probe proposals.
- **No false-positive increase:** C4 remained 0; both **T07** and **T09** controls stayed C1.
- **No legality/retry activity** on either run (C5 = 0).
- **Overall miss rate unchanged** at the rubric level (C3 count flat) — calibration did not broadly unlock emission.
- **C8 slight increase** (+1): more beats wrote physical transition fiction while still choosing `no_covered_change` — suggests prompt examples may sharpen beat authoring without always flipping evaluation (or rubric sensitivity to fiction/evaluation mismatch).

---

## 6. Transitional-edge-case evaluation

| Case | Expected | v3 baseline | v3 calibrated | Overfire? |
|------|----------|-------------|---------------|-----------|
| Doorway / immediate return (T03) | nuanced; often no-change if tethered | `no_covered_change` | `no_covered_change` | No |
| Present disengaged (T07) | no-change | C1 | C1 | No |
| Passive observer (T09) | no-change | C1 | C1 | No |
| Remote phone (T05) | covered | C3 | C2 | No |
| Clean exit (T01) | covered | C3 (exit beats, no proposal) | C3 | No |
| Offscreen filler | should not dominate | n/a — no spurious remote chatter | n/a | No |

**Qualitative:** T03 beats in both runs showed threshold/doorway motion with same-beat return intent; both models chose `no_covered_change` — **aligned with preservation goal**, not aggressive exit detection. Calibrated T05 beats placed Celina at kitchen phone calling Ayame; only calibrated run emitted `off_focal` proposal.

---

## 7. Remaining ontology gaps

1. **Clean exit / reentry (T01/T02/T10):** beats often depict spatial change but evaluation stays `no_covered_change` — gap persists beyond focal-participation wording.
2. **Immediate-return (T03):** rubric expects `covered_change` but model behavior may be *correctly* nuanced; manifest may need dual acceptable classes.
3. **2-char capsule absence:** ACTIVE SCENE FOCUS / PARTICIPATION ARC still absent (`should_emit_social_focus_capsule` false) — state-derived “in the room” pressure remains un tested in 2-char matrix.
4. **Proposal schema friction:** v2 runs still show parse retries when models emit malformed `semantic_evaluation.proposals` (character field, extra keys) — orthogonal but noisy.
5. **Social continuity > physical continuity:** models still author socially tethered displacement (phone call, hallway) without proposals unless calibration explicitly primes remote channel (T05).

---

## 8. Findings to append vs promote into issues

| Finding | Destination |
|---------|-------------|
| Participation ontology gap (physical/remote/transitional) | **Append #240**, cross-ref **#225** validation notes |
| Harness redaction confound (`"into "` heuristic) | **Append #240** + `SCENARIO_VALIDATION_FRAMEWORK.md` (done) |
| Forced-speaker + offstage reentry for probe matrix | **Append #240** harness notes; optional sub-issue if promoting to reusable test infra |
| Remote phone emission lift from calibration A | **Append #240** calibration track; input to **#243** offline eval |
| T03 immediate-return rubric ambiguity | **New sub-issue** under #240 or #243 — rubric vs nuanced no-change |
| 2-char omission of focus/arc capsules | **Append #227** / **#240** — explains persistent “in the room” mismatch in 4-char cases |
| Willow intelligent tethering (social > physical) | **Append #225** — preserve as behavioral discovery |
| Offscreen posting / filler concern | **Append #225** / **#243** — no evidence of overfire in controls |
| `issue240_semantic_evaluation` topology registration | **Append #240** — bugfix note for experimental aliases |
| Architecture redesign (multi-axis states, universal adjudication) | **Not promoted** — out of scope |

---

## 9. Recommended next governance action

1. **Append harness v3 results to #240** with links to `session_897` / `session_898` artifacts and this report.
2. **Decide on calibration A disposition:** keep as investigation alias; do **not** promote to default — signal too weak except remote phone; rerun after capsule policy for 2-char probes if state pressure is in scope.
3. **Open a small #240 sub-issue** for immediate-return rubric dual-class (`covered_change` vs acceptable `no_covered_change`) before tuning prompts further.
4. **Schedule #243 offline eval** comparing 897 vs 898 jsonl with human review of T03/T05/T07 fiction-vs-evaluation pairs.
5. **Optional:** commit this branch as an investigation checkpoint (prompt variant + harness + report only).

---

## Files modified (exact)

- `autogen_rp/python/rp_app/prompt_topology_issue240.py`
- `autogen_rp/python/rp_app/issue240_semantic_evaluation.py`
- `autogen_rp/python/rp_app/user_trigger_schedule.py`
- `autogen_rp/python/rp_app/turn_runner.py`
- `autogen_rp/python/rp_app/headless_simulation_runner.py`
- `autogen_rp/python/scripts/run_scene_simulation_llm.py`
- `autogen_rp/python/scripts/compare_participation_calibration_ab.py` *(new)*
- `autogen_rp/python/data/issue240/i240_emission_probe_schedule_v1.json`
- `autogen_rp/python/tests/test_issue_240_prompt_topology.py`
- `autogen_rp/python/tests/test_issue240_actor_targeted_overlay.py`
- `autogen_rp/python/tests/test_issue240_semantic_evaluation.py`
- `SCENARIO_VALIDATION_FRAMEWORK.md`
- `autogen_rp/python/validation_runs/participation_calibration_ab_implementation_report.md` *(this file)*

## Extraction artifact paths (v3)

| Run | JSONL | CSV | Summary |
|-----|-------|-----|---------|
| Baseline 897 | `validation_runs/emission_map_baseline_v3.jsonl` | `..._v3.csv` | `..._v3_summary.json` |
| Calibrated 898 | `validation_runs/emission_map_calibrated_v3.jsonl` | `..._v3.csv` | `..._v3_summary.json` |
| Comparison | `validation_runs/participation_calibration_ab_comparison_v3.json` | — | — |

Audit roots: `rp_app/data/rp_audits/session_897/`, `session_898/`
