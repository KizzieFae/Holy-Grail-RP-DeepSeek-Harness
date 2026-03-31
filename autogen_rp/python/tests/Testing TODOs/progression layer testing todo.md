Progression Layer — Test Sheet (Pass / Fail)

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