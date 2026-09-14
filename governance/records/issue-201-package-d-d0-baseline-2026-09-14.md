# Issue #201 — Package D D0 Baseline Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` (Package D — **D0 baseline only**; no ablations)  
**Assigned / effective weight:** `full` / `full`  
**Control substrate SHA:** `c751ea666f0cae6524698005aa5859721c2e9738` (post-#206 / PR #207)  
**Harness:** `v2/rp_runtime/scripts/issue201-package-d-d0-baseline.mjs`  
**Evidence root:** `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/`

---

## 1. Resume / bootstrap synchronization evidence

| Check | Result |
|-------|--------|
| Full-bootstrap profile | **Confirmed** — `docs/issue-bootstrap-profiles.md` Full list; prior #201 activation + Packages A–C + Stage-1 records on file |
| Session resume | Continuation of existing #201 cycle (not new Issue) |
| Prior A–C evidence | `governance/records/issue-201-packages-abc-investigation-2026-09-14.md` — present |
| Prior Stage-1 evidence | `governance/records/issue-201-package-d-stage1-2026-09-14.md` — present (blocker documented) |
| #206 handoff | Not re-investigated; integrated closure SHA adopted as D0 control |
| Harness methodology | Package D production `submitUserTurn` path; blind-eval `issue201_blind_eval_packet_v1` |
| `DEEPSEEK_API_KEY` | Present |
| Character cards | Local `data/characters/` (harley_quinn, poison_ivy, magpie, ayame, kizzie) |

**Discrepancy check:** User handoff state matches authoritative GitHub #201 and integrated `main` HEAD. **No material disagreement.**

---

## 2. Exact #201 Issue / Project state

| Field | Value |
|-------|-------|
| State | OPEN |
| `Current status:` | `investigating` |
| Labels | `enhancement`, `type:design_gap` |
| Project #10 | **Status:** In Progress / **Workflow:** Investigating / **Priority:** P1 |
| Packages A–C | Accepted |
| Package D | D0 baseline **completed** this session |
| Ablations (EXP-1/2/3, D-01–D-10) | **NOT executed** |
| Production redesign | NOT authorized |

`gh issue view 201 --json number,state,labels,projectItems` and `gh project item-list 10` (issue row **#201**, `priority: P1`, `workflow: Investigating`) verified 2026-09-14.

---

## 3. Exact integrated control SHA

| Anchor | SHA |
|--------|-----|
| Expected (#206 closure) | `c751ea666f0cae6524698005aa5859721c2e9738` |
| `git rev-parse HEAD` at D0 run | `c751ea666f0cae6524698005aa5859721c2e9738` |
| Match | **Yes** |

---

## 4. #206 blocker resolution in real D0 path

| Evidence | Result |
|----------|--------|
| Prior failure | `disallowed source_kind 'authoritative_perceptual_inventory' for inference_kind 'character_orientation'` (Stage-1 D0 attempt) |
| D0 Arkham runs | `character_orientation` executed **2× per run** (Poison Ivy + Harley lanes); **no manifest policy rejection** |
| D0 Ayame runs | `character_orientation` executed **1× per run**; **no rejection** |
| `character_orientation_evidence` flag | `true` on all 4 runs |
| Round completion | 4/4 committed |

**Conclusion:** #206 / PR #207 parity fix is **validated on the live D0 production path.**

---

## 5. Arkham control configuration

| Parameter | Value |
|-----------|-------|
| Scenario | `arkham_asylum_mess_hall_arena` |
| Path | Production `HolyGrailApplicationClient.submitUserTurn` |
| Characters | `harley_quinn`, `poison_ivy`, `magpie` |
| Roles | instigator / instigator_accomplice / new_arrival |
| Player | `magpie` (`Magpie`) |
| Opener | `mess_hall_magpie` (template) |
| Player stimulus | Magpie observes guard's gold watch; provocative murmur toward Harley |
| Architecture | A4 incumbent (unmodified) |
| Execution evidence | Enabled under investigation root |

---

## 6. Arkham repetition count and rationale

**Count:** 2 (`D0-arkham_stress-r1`, `D0-arkham_stress-r2`)

**Rationale:** Governance minimum for stochastic instability screening. Both runs committed with objective correctness clean. Wall-time delta **6%** (302.7s vs 285.7s); inference count 88 vs 84. **No third repetition authorized** — variance is moderate on path fan-out (librarian_mediation 10 vs 2 calls) but not material on contractual dimensions or selected-character outcome (Poison Ivy both runs).

---

## 7. Ayame control configuration

| Parameter | Value |
|-----------|-------|
| Scenario | `ayame_household_entry_evaluation` |
| Path | Production `submitUserTurn` |
| Characters | `ayame`, `kizzie` |
| Roles | host / applicant |
| Player | `kizzie` (`Kizzie`) |
| Stimulus | F06 knock path — double-check house number, knock |
| Architecture | A4 incumbent (unmodified) |

---

## 8. Ayame repetition count and rationale

**Count:** 2 (`D0-ayame_controlled-r1`, `D0-ayame_controlled-r2`)

**Rationale:** Default two-repetition controlled comparison. Both committed; PVR valid. Wall-time spread **20%** (157.3s vs 188.5s) driven largely by librarian_mediation fan-out (2 vs 8 calls) and post-commit section (44.4s vs 121.3s). Semantic outputs are structurally similar (door opens, invitation inside) with modest prose variance. **No third repetition** — sufficient for D0 characterization; ablation comparisons should hold scenario/opener constant and note path fan-out as observability noise.

---

## 9. Per-run wall time (player-submit → visible presentation)

| Case | Wall (s) | Player-visible latency (ms) | Session |
|------|----------|----------------------------|---------|
| D0-arkham_stress-r1 | 302.7 | 302,670 | `hg-session-fca85cb2-ab17-41f8-9a70-4fd05f8b38ff` |
| D0-arkham_stress-r2 | 285.7 | 285,663 | `hg-session-b167d8a6-628c-4faf-ac08-bf2d3c4b5fea` |
| D0-ayame_controlled-r1 | 157.3 | 157,310 | `hg-session-9593fae5-2321-4dfb-aefe-61762a9f0568` |
| D0-ayame_controlled-r2 | 188.5 | 188,417 | `hg-session-f7bbe33f-e087-427f-a638-13596934abc3` |

---

## 10. Per-run stage timing (latency reconstruction excerpts)

| Case | Char-turn CP (ms) | Post-commit section (ms) | Top inference stages (wall ms) |
|------|-------------------|--------------------------|--------------------------------|
| arkham-r1 | 24,328 | 125,101 | librarian_mediation 103,996 (10×); narrator_environment_cognition 73,287 (3×); player_decomposition 26,983 |
| arkham-r2 | 31,722 | 64,399 | librarian_mediation 42,840 (2×); narrator_environment_cognition 42,216 (3×); narrator_presentation 28,571 |
| ayame-r1 | 34,157 | 44,442 | player_decomposition 36,609; librarian_mediation 32,077 (2×); character_orientation 12,372 |
| ayame-r2 | 25,659 | 121,338 | librarian_mediation 84,282 (8×); player_decomposition 30,536; narrator_environment_cognition 26,883 |

Full reconstruction: `outputs/D0-*-latency.txt` per run.

**Note:** `round_internal_critical_path` reports `pre_commit_serial_graph_missing` (bounded_partial) — consistent with prior #194 instrumentation limits; player-visible latency is proven.

---

## 11. Per-run inference count

| Case | Total attempts | Distinct LLM inference kinds (excl. lifecycle spans) | Retries |
|------|----------------|------------------------------------------------------|---------|
| arkham-r1 | 88 | ~20 kinds | 0 |
| arkham-r2 | 84 | ~20 kinds | 1 |
| ayame-r1 | 52 | ~15 kinds | 1 |
| ayame-r2 | 56 | ~15 kinds | 0 |

Arkham ~2× Ayame inference volume (multi-character stress + env cognition depth).

---

## 12. Per-run token / reasoning usage

| Case | Input tokens | Output tokens | Reasoning tokens (summed) |
|------|-------------|---------------|---------------------------|
| arkham-r1 | 120,454 | 68,247 | 38,661 |
| arkham-r2 | 86,071 | 48,190 | 31,240 |
| ayame-r1 | 41,979 | 26,112 | 14,119 |
| ayame-r2 | 69,393 | 39,671 | 17,987 |

Token totals derived from execution-evidence attempts (some lifecycle rows lack token fields).

---

## 13. Retries / failures

| Case | Infrastructure failures | Retries | Retry detail |
|------|------------------------|---------|--------------|
| All 4 | **0** | 2 total | `character_move` attempt_index=1 on arkham-r2 and ayame-r1; both finished `stop` and round committed |

No new blockers. Retries are **character semantic-move correction**, not manifest or contract failures.

---

## 14. Contractual-correctness findings

| Dimension | Finding |
|-----------|---------|
| PVR validation | **valid** on all 4 runs (4 PVR units Arkham; Ayame per run) |
| Round commit | **4/4 committed** |
| Knowledge-boundary violations | **None detected** in automated harness checks |
| Perceptual-boundary violations | **None flagged** (no invalid PVR) |
| Continuity / state errors | **Not auto-detected**; no round abort |
| Player-action loss | Player stimulus reflected in NPC responses (watch/knock) |
| Missed required responses | N/A — single character turn selected per round (`no_eligible_actors` after first response) |
| Authoritative/derived discrepancies | **Not probed** to #200 F06 depth in this harness pass |
| Forensic completeness | Execution evidence + latency reconstruction **present** for all runs |

**Poor RP prose is not a blocker** — all runs are baseline evidence.

---

## 15. Preserved visible-output / evidence locations

| Artifact | Path |
|----------|------|
| Machine report | `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/issue201-d0-baseline-report.json` |
| Presentations | `.../outputs/D0-*-presentation.txt` |
| Latency | `.../outputs/D0-*-latency.txt` |
| Blind packet | `.../outputs/issue201-d0-blind-eval-packet.json` |
| Answer key (restricted) | `.../outputs/issue201-d0-blind-eval-answer-key.json` |
| Execution evidence | `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/hg-session-*/` |

---

## 16. Blind semantic baseline results

**Procedure:** `issue201_blind_eval_packet_v1` — architecture labels stripped; evaluator scored blind labels A–D before unmasking.

**Scale:** 1 (poor) – 5 (strong). Dimensions separated from contractual checks.

| Blind | Scenario (unmasked) | Fid. | Dist. | Init. | Resp. | Prog. | Coh. | Prose | Low rep. | Low stiff. | Low expos. | Emo. cont. | **Mean** |
|-------|---------------------|------|-------|-------|-------|-------|------|-------|----------|------------|------------|------------|----------|
| A | arkham-r1 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 3 | 4 | **3.8** |
| B | arkham-r2 | 4 | 4 | 4 | 4 | 4 | 4 | 3 | 4 | 3 | 3 | 4 | **3.7** |
| C | ayame-r1 | 4 | 3 | 4 | 5 | 4 | 5 | 4 | 4 | 3 | 3 | 4 | **3.9** |
| D | ayame-r2 | 4 | 3 | 4 | 5 | 4 | 5 | 4 | 3 | 3 | 3 | 4 | **3.8** |

**Blind observations (pre-unmask):** All samples show competent host/NPC voice, clear scene grounding, and responsiveness to player stimulus. Arkham samples exhibit Ivy tactical control; Ayame samples are ceremonially formal with low distinctiveness (single speaker). Stiffness and exposition scores cluster at 3 — consistent with prior F06 stiffness hypothesis but **not causally attributed** here.

---

## 17. Run-to-run variance analysis

### Arkham (2 runs)

| Metric | r1 | r2 | Δ |
|--------|----|----|---|
| Wall (s) | 302.7 | 285.7 | −6% |
| Inferences | 88 | 84 | −5% |
| librarian_mediation calls | 10 | 2 | **high path variance** |
| Selected character | Poison Ivy | Poison Ivy | stable |
| Semantic mean | 3.8 | 3.7 | stable |

### Ayame (2 runs)

| Metric | r1 | r2 | Δ |
|--------|----|----|---|
| Wall (s) | 157.3 | 188.5 | +20% |
| Inferences | 52 | 56 | +8% |
| librarian_mediation calls | 2 | 8 | **high path variance** |
| Post-commit (ms) | 44,442 | 121,338 | +173% |
| Selected character | Ayame | Ayame | stable |
| Semantic mean | 3.9 | 3.8 | stable |

**Assessment:** Contractual outcomes stable; **latency and mediation fan-out are the primary D0 noise sources** for future ablation pairing.

---

## 18. Comparison with historical F06 / #194 evidence

| Source | Scenario | Wall (s) | Inferences | Notes |
|--------|----------|----------|------------|-------|
| Repeat F06 (#201 body) | ayame | 156.8 / 192.6 | 38 each | Pre-#199/#200 session `f883b2dd` |
| D0 ayame-r1/r2 | ayame | 157.3 / 188.5 | 52 / 56 | Post-#206 control; **similar wall band** |
| D0 arkham | arkham | 285.7–302.7 | 84–88 | **~2× ayame wall**; new stress baseline |

Historical F06 timings are **contextually aligned** for ayame wall-clock but **not used as causal control**. Inference count increased vs historical 38/round (instrumentation / path differences — not concluded as architecture regression).

---

## 19. World-state / portal / pressure observations

**Deferred #200 questions — observe only, no remediation:**

| Topic | D0 observation |
|-------|----------------|
| Player-action promotion to authoritative world state | Knock/watch stimuli reflected in **presentation**; harness did not assert Continuity promotion of tier-1 observables |
| Portal / narrative door state | Ayame runs: door opens in presentation; **no automated portal-authority check** |
| Pressure freshness | `storyteller_post_commit_issue_pressure` ran on all 4 rounds; magnitudes 6.3–8.8s wall; **content not audited** for stale semantic_unmet_condition |
| `storyteller_round_summary` | **null** on all D0 runs (field present but empty in round result) |

Classifications from Stage-1 record **remain deferred** — recurrence alone does not settle architecture.

---

## 20. Forensic completeness assessment

| Layer | Status |
|-------|--------|
| Execution evidence per session | **Complete** (attempt JSON + index) |
| Player-visible latency | **Proven** (reconstruction matches wall within ~40ms) |
| Per-inference tokens (LLM) | **Mostly complete**; lifecycle/span rows omit tokens |
| Pre-commit serial CP graph | **Partial** (`pre_commit_serial_graph_missing`) |
| Presentation preservation | **Complete** (full text files) |
| Blind-eval packet | **Complete** |

**Sufficient for Package D ablation forensics** at the level demonstrated in #194, with known CP-graph gap documented.

---

## 21. Control-substrate stability assessment

| Criterion | Assessment |
|-----------|------------|
| 1. Execution reliability | **Stable** — 4/4 success post-#206 |
| 2. Forensic completeness | **Adequate** (see §20) |
| 3. Objective correctness stability | **Stable** — zero harness-flagged contractual issues |
| 4. Latency/token variability | **Moderate–high** — librarian_mediation fan-out and post-commit tail |
| 5. Semantic RP-quality variability | **Low–moderate** within scenario pairs |

---

## 22. D0 sufficiency for causal ablation

**Determination (for Governance; Implementation-AI does not self-authorize):**

The incumbent **A4 control substrate is sufficiently stable and observable** to **begin** bounded causal ablation **subject to Governance authorization**, with these caveats:

1. Pair ablation runs on the **same scenario/opener/stimulus** and report mediation fan-out alongside wall time.
2. Treat librarian_mediation call-count variance as **experimental noise**, not ablation effect, unless isolated.
3. Ayame remains the **controlled** comparator; Arkham the **stress** comparator.
4. Do not use pre-D0 historical sessions as ablation controls.

**Not authorized in this step:** EXP-1/2/3 or D-01–D-10.

---

## 23. New blockers

**None.** #206 blocker cleared. No environmental/transient failures in D0.

---

## 24. Durable evidence locations

| Type | Location |
|------|----------|
| This report | `governance/records/issue-201-package-d-d0-baseline-2026-09-14.md` |
| D0 harness | `v2/rp_runtime/scripts/issue201-package-d-d0-baseline.mjs` |
| Prior Package D Stage-1 | `governance/records/issue-201-package-d-stage1-2026-09-14.md` |
| Raw run bundle | `data/investigation_runs/issue201-d0-baseline-2026-09-14T07-46-14-584Z/` |

---

## 25. Artifact disposition

| Artifact | Disposition | Reason |
|----------|-------------|--------|
| `governance/records/issue-201-package-d-d0-baseline-2026-09-14.md` | **Commit** (authorized #201 evidence) | Durable governance record |
| `v2/rp_runtime/scripts/issue201-package-d-d0-baseline.mjs` | **Commit** | Authorized investigation harness (D0-only) |
| `data/investigation_runs/issue201-d0-baseline-*` | **Retain local; gitignored** | `data/*` policy — runtime investigation output |
| `governance/records/issue-201-package-d-stage1-2026-09-14.md` | **Retained** | Historical blocker context |
| Stage-1 harness `issue201-package-d-stage1.mjs` | **Retained** | Future ablation tranche (not executed) |
| Untracked `_commit-msg` / `_pr` staging files (if any) | **Unrelated to #201** — do not merge into this record |

---

## 26. Recommended first experimental tranche (not executed)

Based on Packages A–C + fresh D0 evidence (unchanged ranking logic from Stage-1, now **unblocked**):

| Order | Experiment | Rationale |
|-------|------------|-----------|
| 1 | **EXP-1 / D-01** | `skipStorytellerCognition` + `skipPlotCognitionOrchestration` — largest preamble uncertainty |
| 2 | **EXP-2 / D-06** | `directorSemanticQaEnabled: false` — isolate Director QA marginal cost |
| 3 | **EXP-3 / D-03** | `skipCharacterKnowledgeCognition` — orientation bypass (Stage-2 mandate; supersedes Stage-1 Storyteller-only label) |

Run each against **fresh matched controls** on both Arkham (≥2) and Ayame (≥2) when authorized.

---

## 27. Questions requiring Governance decision

1. **Authorize Package D Stage-1 tranche** (EXP-1, EXP-2, EXP-3) on control SHA `c751ea6+`?
2. **Repetition policy:** require 3rd control repetition when librarian_mediation fan-out differs by >4×, or accept paired comparison with fan-out noted?
3. **World-state promotion gap:** include observability assertions in ablation harness, or continue observe-only through D?
4. **Human blind eval:** supplement Implementation-AI rubric scores with human evaluator pass?
5. **Issue body update:** refresh execution snapshot with D0 SHA and evidence paths?

---

## Session boundary

**Status remains:** `investigating` — In Progress / Investigating / P1  
**Completed this session:** D0 baseline only (4 production control runs + blind eval + sufficiency determination).  
**Not executed:** Any ablation, consolidation, or Packages E–G synthesis.
