Progression Layer — Test Sheet (Pass / Fail)

**v1 checkpoint (validated):** [progression layer validation status v1.md](./progression%20layer%20validation%20status%20v1.md) — official progression layer validation status and behavioral summary.

## 0. Automated baseline (before manual checklist)

From `autogen_rp/python`:

```bash
# Deterministic regression (no API calls for progression contract)
pytest tests/test_progression_enforcement.py tests/test_turn_runner_updates.py tests/test_orchestration_helpers.py -q

# Optional: live DeepSeek checks (requires DEEPSEEK_API_KEY)
pytest tests/test_progression_layer_llm.py -m progression_llm -v

# Fast local run excluding any test marked llm
pytest -m "not llm"

# Simulation pipeline (scripted moves through production continuity, then read the printed audit)
python scripts/run_progression_layer_simulation.py
python scripts/run_presence_scene_audit.py

# Full production turn runner, headless (Director + character + Narrator LLMs; same path as Streamlit)
python scripts/run_scene_simulation_llm.py --list-scenarios
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --turns 6 --audit
# Baseline (enforcement off) vs treatment — compare JSON metrics / audits
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --no-progression-enforcement --metrics-out ./out/baseline.json
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --metrics-out ./out/treatment.json --verdict WARN --failure-class retry
# failure-class when FAIL/WARN: contract | gate | selection | retry | continuity | other

# Manifest-only regression (no API)
pytest tests/test_progression_simulation_scenarios.py -q
```

The first two are **deterministic** (no LLM). `run_scene_simulation_llm.py` uses **`turn_runner.run_character_turns`** with DeepSeek (`DEEPSEEK_API_KEY`). Fixed setups live in `rp_app/data/progression_simulation_scenarios/*.json`. Use **`--audit`** to write **`rp_app/data/rp_audits/`** JSON (same logger as Streamlit). Stdout markdown is the quick human summary; audit files support checklist **H** and failure triage.

Overarching workflow and scenario catalog: **`SCENARIO_VALIDATION_FRAMEWORK.md`** at the **repository root** (next to `ARCHITECTURE_OVERVIEW.md`).

**Hard rule:** validation **observes / classifies / reports** and **stops**; **no** automatic code, scenario, prompt, or threshold changes after a run. Triage → record layer + verdict + repro → **stop** unless a human explicitly directs remediation. See framework **Constraints** + **`DEBUGGING_GUIDE.md` → Validation vs Remediation Boundary**. **Invalid runs:** framework **Validation retry policy (invalid runs)** — triage first, manual rerun only, **≤2–3 retries** per scenario per goal, then different scenario / redesign / rescope (not remediation).

If a run looks wrong but the symptom might be **presence, exit, continuity, selection, or encoding**, use **`DEBUGGING_GUIDE.md` → Simulation failure triage (layer-aware deep-dive)** before any fix — and **do not** implement the fix in the same pass without explicit approval.

**Mapping (high level)**

| Checklist area | Mostly covered by |
|----------------|-------------------|
| A (architecture integrity) | Unit/integration: `test_progression_enforcement.py`, `test_turn_runner_updates.py`, `turn_runner_turn` flow; manual for “no duplicate events” in long runs |
| B (Q1–Q4 contract) | `test_progression_enforcement.py`; `test_progression_layer_llm` (character + continuity) |
| C (gate OR) | Code review + `progression_enforcement_gate_active` usage; optional manual/audit |
| D (retry) | Code path in `turn_runner_turn.py`; audit logs `validation_progression_retry` |
| E (MED→HIGH) | `test_orchestration_helpers.py` |
| F (scene quality) | **Subjective** — `run_scene_simulation_llm.py` for full-pipeline signal; §I scenarios; narrow pytest LLM probes |
| G (continuity safety) | Existing suite + scenario runs |
| H (auditability) | `run_scene_simulation_llm.py --audit` + `rp_audits/`; manual Streamlit sessions; deterministic scripts for stdout-only |

---

Instructions (manual sheet)

Run each scenario
Mark each item:
PASS
FAIL
WARN (minor issue, not blocking)
Add short notes where useful
A. Architecture Integrity
Check	Result	Notes
No continuity mutation from progression layer	☐ PASS ☐ FAIL ☐ WARN	
process_turn runs exactly once per accepted turn	☐ PASS ☐ FAIL ☐ WARN	
Failed attempts leave no trace in continuity	☐ PASS ☐ FAIL ☐ WARN	
Failed attempts produce no visible narration/chat	☐ PASS ☐ FAIL ☐ WARN	
Snapshot/restore fully resets state on retry	☐ PASS ☐ FAIL ☐ WARN	
No duplicate events, issues, or outcomes appear	☐ PASS ☐ FAIL ☐ WARN	
B. Progression Contract Behavior
Check	Result	Notes
Turns qualify only via Q1–Q4 signals	☐ PASS ☐ FAIL ☐ WARN	
Dialogue-only turns do not qualify	☐ PASS ☐ FAIL ☐ WARN	
Cosmetic/environment-only turns do not qualify	☐ PASS ☐ FAIL ☐ WARN	
Issue changes correctly qualify progression	☐ PASS ☐ FAIL ☐ WARN	
Presence changes correctly qualify progression	☐ PASS ☐ FAIL ☐ WARN	
Bounded scene-state updates qualify correctly	☐ PASS ☐ FAIL ☐ WARN	
Repeated consequence strings do not trivially bypass	☐ PASS ☐ FAIL ☐ WARN	
C. Gate Behavior
Check	Result	Notes
Beat shift forces progression on correct turn	☐ PASS ☐ FAIL ☐ WARN	
High stall pressure triggers enforcement	☐ PASS ☐ FAIL ☐ WARN	
Enforcement does NOT trigger in low-pressure scenes	☐ PASS ☐ FAIL ☐ WARN	
OR logic (beat shift OR high pressure) behaves correctly	☐ PASS ☐ FAIL ☐ WARN	
D. Retry Behavior
Check	Result	Notes
Retry triggers when progression fails	☐ PASS ☐ FAIL ☐ WARN	
Retry count is correctly capped	☐ PASS ☐ FAIL ☐ WARN	
Retry produces improved outcome (not same failure)	☐ PASS ☐ FAIL ☐ WARN	
Retry does not consume beat-shift prematurely	☐ PASS ☐ FAIL ☐ WARN	
Retry does not create duplicate state changes	☐ PASS ☐ FAIL ☐ WARN	
Audit clearly shows retry cause	☐ PASS ☐ FAIL ☐ WARN	
E. Selection Behavior
Check	Result	Notes
MED→HIGH override triggers under pressure	☐ PASS ☐ FAIL ☐ WARN	
Override respects available actor pool	☐ PASS ☐ FAIL ☐ WARN	
Override improves progression success rate	☐ PASS ☐ FAIL ☐ WARN	
Override does not break direct address rules	☐ PASS ☐ FAIL ☐ WARN	
No new selection instability introduced	☐ PASS ☐ FAIL ☐ WARN	
F. Scene Outcome Quality
Check	Result	Notes
Verbal loops break earlier than before	☐ PASS ☐ FAIL ☐ WARN	
Accepted turns produce real change, not noise	☐ PASS ☐ FAIL ☐ WARN	
Scenes move forward without feeling forced	☐ PASS ☐ FAIL ☐ WARN	
Character voice remains consistent	☐ PASS ☐ FAIL ☐ WARN	
Characters do not become unnaturally “action-driven”	☐ PASS ☐ FAIL ☐ WARN	
Quiet/observational beats still work when allowed	☐ PASS ☐ FAIL ☐ WARN	
G. Continuity Safety
Check	Result	Notes
No issue lifecycle regressions	☐ PASS ☐ FAIL ☐ WARN	
No presence/offstage regressions	☐ PASS ☐ FAIL ☐ WARN	
No grounding/state marker regressions	☐ PASS ☐ FAIL ☐ WARN	
No phantom or duplicate resolved outcomes	☐ PASS ☐ FAIL ☐ WARN	
Save/load works correctly after retries	☐ PASS ☐ FAIL ☐ WARN	
H. Auditability
Check	Result	Notes
Progression requirement clearly logged	☐ PASS ☐ FAIL ☐ WARN	
Qualification result clearly logged	☐ PASS ☐ FAIL ☐ WARN	
Retry cause clearly visible	☐ PASS ☐ FAIL ☐ WARN	
Beat shift + stall score traceable per turn	☐ PASS ☐ FAIL ☐ WARN	
Easy to diagnose false positives/negatives	☐ PASS ☐ FAIL ☐ WARN	
I. Scenario Runs

Run each scenario and evaluate holistically:

Scenario	Result	Notes
Arrival / setup scene	☐ PASS ☐ FAIL ☐ WARN	
2-character emotional loop	☐ PASS ☐ FAIL ☐ WARN	
3-character conflict	☐ PASS ☐ FAIL ☐ WARN	
Strong user steer (beat shift)	☐ PASS ☐ FAIL ☐ WARN	
Passive observer scene	☐ PASS ☐ FAIL ☐ WARN	
Long session (20+ turns)	☐ PASS ☐ FAIL ☐ WARN	
Recovery from derail	☐ PASS ☐ FAIL ☐ WARN	
Final Gate (Decision)
Condition	Result
All critical architecture checks pass	☐ YES ☐ NO
No continuity corruption observed	☐ YES ☐ NO
Retry system stable	☐ YES ☐ NO
Scene quality improved vs baseline	☐ YES ☐ NO
No major regressions introduced	☐ YES ☐ NO
Verdict
☐ READY FOR PRODUCTION (v1)
☐ NEEDS TUNING
☐ BLOCKED — FIX REQUIRED

---

## Refinements (agreed adjustments)

- **Separate “automated” vs “manual”**: Rows in **F** and much of **H** are inherently subjective or audit-visual; treat **WARN** as normal there unless you define measurable criteria (e.g. “retry stage appears in `_audit_summary`”).
- **B / “cosmetic/environment-only”**: Clarify that “qualify” means **Q1–Q4 after `process_turn`**, not “no environment_event in Director JSON.” Environment can still qualify if continuity maps it into consequences/events.
- **D / “Retry does not consume beat-shift prematurely”**: Beat-shift is consumed in **`apply_successful_turn_updates` after a successful narrated turn**; a failed progression retry **before** narration should **not** consume it. Verify with audit + one scripted run.
- **E / “Override improves progression success rate”**: Treat as **hypothesis** — log before/after in manual runs; hard to PASS/FAIL in one session without baseline.
- **A / “No duplicate events”**: Define “duplicate” (same `turn_index`, same summary, etc.) or keep as manual spot-check.
- **Prerequisite**: `DEEPSEEK_API_KEY` for LLM rows; `test_deepseek_api_key_exists` still **requires** the key in environments that run the full suite without `-m "not llm"` exclusions.

---

## Validation checkpoint — initial LLM runs (baseline vs treatment)

**Status:** Results match expectations. This is a **strong initial** check of progression enforcement. The framework did what it was built for.

### Assessment

- Baseline vs treatment comparison **worked as intended**.
- Treatment **consistently improved** structured progression metrics.
- No obvious regressions in coherence, continuity, or character behavior in these runs.

**Verdicts (initial pass):**

- **emotional_loop_2char** — **PASS** (valid).
- **conflict_3char** — **PASS** (valid).
- **strong_user_steer** — **WARN** (valid until the garbled-character text issue is understood).

### Limitations (identified)

1. **Turn depth (2-character scenes)** — The harness effectively caps at **two bot replies per user message** when only two characters are present (`min(max_turns, bot_count)`). These runs were **short-form** validation, not full sustained-pressure validation: hard to see long stalls, plateau recovery, or retry under stress.
2. **Retry paths not exercised** — No progression retries and no failed attempts in this batch. Gate-under-failure, retry correctness, and recovery are **not yet validated** by these runs.
3. **Text corruption (strong_user_steer)** — Likely encoding or rendering; **not** treated as a progression-layer logic failure, but must be investigated and not ignored.

### Next steps (required — validation only)

**Do not:** redesign progression logic, tune thresholds, add metrics, or expand the scenario framework until the below is done.

1. **Deeper runs (multi-turn pressure)**  
   - **Option A (preferred):** Use **3-character** scenarios: `conflict_3char`, `passive_observer`, and **`long_session`** (critical). Aim to observe behavior over **many turns** (e.g. 5–10+ bot steps where the runner allows).  
   - **Option B:** If needed, adjust the headless runner so **2-character** scenes can exceed two bot lines per user round when scenarios call for it.

2. **Force retry conditions** — Deliberately set up runs (e.g. emotional_loop-style pressure) where non-qualifying / loop-prone turns are likely. Confirm gate, retry, and improved outcome; critical before calling the layer production-ready.

3. **Re-run strong_user_steer** — Check if garbled text reproduces; narrow to encoding vs model vs narrator formatting.

4. **Light repeatability** — For at least one scenario, run treatment **2–3×**; compare structured metrics and overall behavior.

### Phase goal

Confirm that under **sustained** pressure the system **keeps progression healthy**, **handles failures**, and **recovers via retry** without ruining scene quality. After that, the layer can be treated as **production-ready** for v1.

### Current summary

Progression enforcement is **functionally sound** and **measurably better than baseline** in the initial runs, but **not fully validated** under stress, retries, or long horizons yet.

### Deep simulation (follow-up runs)

`run_scene_simulation_llm.py` with **`--scenario`** now defaults to **deep mode**: full `max_turns` / `--turns` and repeat speakers in one simulated user round. Use **`--no-deep-simulation-turns`** only when you intentionally want the old two-bot / three-bot short cap. See **SCENARIO_VALIDATION_FRAMEWORK.md** → *Deep simulation (headless)*.

### Phase 2 — deeper LLM runs (executed)

Artifacts: `autogen_rp/python/runs/progression_val/phase2/*.json`; audits **083–093**.

| Run | Notes |
|-----|--------|
| **conflict_3char** baseline | 8 turns, all qualifying, no retries. |
| **conflict_3char** treatment | 8 turns, **5 progression retries**, **3 failed attempts**, 7 qualifying / 1 non-qualifying — **retry path exercised**; review session **084** audit for retry quality. |
| **passive_observer** baseline / treatment | 5 turns each; no retries; observer intent unchanged at a glance — **PASS** on “no forced observer center stage” pending your prose read. |
| **long_session** (`--turns 12`) | **Superseded by Phase 2b** (below). Original stop was **`presence_exit` bug**: negated “no walking out” matched hard departure; **not** a progression failure. |
| **strong_user_steer** treatment ×2 | Each: **1 progression retry**, 0 failed attempts, 5 turns — retry observed; check prose for garbling. |
| **emotional_loop_2char** treatment ×3 | Metrics: runs 1 & 3 match (first qual **1**, 6/0); run 2 differs (first qual **2**, 5/1) — **mostly stable**, LLM variance as expected. |

### Phase 2b — `long_session` after exit-detection fix (`scene_exit_detection` negation overlap)

**Closed:** False `exit` on prohibition phrasing (“no walking out”) — fixed in repo (per-match skip of `_EXPLICIT_DEPARTURE_RE` overlaps with negated `walking out` spans). Steer / scenario text unchanged.

**Re-evaluation** (deep simulation default, `--turns 12`, `--audit`). Artifacts: `runs/progression_val/long_session_negation_fix/*.json` (local; gitignored). Audits **094** (baseline) / **095** (treatment).

| Mode | `accepted_character_turns` | Progression retries / failed | Notes |
|------|----------------------------|------------------------------|--------|
| Baseline | **12** | 0 / 0 | Full requested depth; initial “long arc” criterion **met** for baseline. |
| Treatment | **10** | 8 / 6 | Stops **before** 12: model gives Ayame a **later, legitimate** `exit` (“walk out that door”); solo Celina then hits **enforcement / qualifying-delta** churn — triage as **`progression_enforcement`** (or gate + cast size), **not** `presence_exit`. |

**Versus Phase 2 table:** Treatment previously looked “better” on a **4-turn** false collapse; the fair comparison is now **12 vs 10** turns with **different endgame physics** — use prose + audit **095** before declaring treatment PASS on long_session.

**Still open:** UTF-8 / mojibake (U+FFFD) in logs; **long_session treatment** follow-up under solo-cast progression (separate issue from the negation bug).

You **can** redo other initial evaluations (e.g. phase 1 shallow trio with `--no-deep-simulation-turns`) anytime for apples-to-apples with the first checkpoint; **long_session** “long arc” analysis should use **Phase 2b** + deep mode, not the superseded Phase 2 row.