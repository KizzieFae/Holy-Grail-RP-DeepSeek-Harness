# Scenario Validation Framework

This file lives at the **repository root** with the other foundational documents (e.g. `ARCHITECTURE_OVERVIEW.md`, `MODULE_INDEX.md`). Paths below such as `autogen_rp/python/...` are relative to that root.

**Canonical document:** This specification is **stable**. Treat it as the authoritative description of behavioral validation in this repo. **Do not expand or rewrite it** unless real usage surfaces a gap; prefer executing the framework over editing it.

## Purpose

This framework defines how the RP system is validated at the behavioral level.

It provides a structured, repeatable way to test system layers using:

- live LLM-driven scene simulations
- deterministic audit artifacts
- scenario-based evaluation

This is not a debugging tool.  
This is a **core validation layer** used throughout development.

---

## Core Principle

All major system behaviors must be validated through **controlled scenario runs**, not just unit tests.

Unit tests verify correctness.  
Scenario validation verifies **emergent behavior**.

---

## Architecture Overview

The framework consists of four parts:

### 1. Scenario Definitions

Structured JSON files describing test situations.

Each scenario defines:

- characters (`character_card_ids`, resolved to character cards under `rp_app`)
- opening context (`opening_description`)
- location
- initial tension / phase (`initial_tension`, `initial_phase`)
- seeded issues (optional; `seed_escalating_issue` + optional `seed_issue` block)
- beat-shift state (optional; `beat_shift_active`)
- turn limit (`max_turns`)
- intended test purpose (`title`, `intent`)
- user trigger (`trigger_text`)
- **optional** `expected_pressure_profile`: `"low"` | `"medium"` | `"high"` — design-time hint for whether advisory/gate pressure should tend low or high (for future checks against missed gate activation or misclassified pressure; does not change runtime today). Omitted on older manifests is fine.

**Storage path** (repository root = Holy Grail RP):

`autogen_rp/python/rp_app/data/progression_simulation_scenarios/<scenario_id>.json`

The `id` field inside the file must match `<scenario_id>` (filename without `.json`).

**Current scenario set**

| `scenario_id` | Focus |
|---------------|--------|
| `arrival_setup` | Low pressure / opening; progression should not over-trigger |
| `emotional_loop_2char` | Two-character loop; enforcement should shorten talk-only stalls |
| `conflict_3char` | Three-character conflict; coherence and progression |
| `strong_user_steer` | Beat-shift on; user steer should produce real change |
| `passive_observer` | Third character witness; avoid forcing unnatural center-stage action |
| `long_session` | 22-turn default; accumulation / continuity drift |
| `recovery_derail` | Off-topic user steer; recovery of progression and grounding |
| `memory_public_propagation` | Public dialogue; observer episodic memory (simulation-primary checks) |
| `memory_private_directed` | Whisper / directed line; boundary vs non-addressee memory |
| `memory_duplicate_retry` | Longer run; bounded memory (duplicate retry exercised in supplemental tests) |
| `memory_fallback_director` | Normal Director JSON path (parse fallback in supplemental tests) |
| `memory_long_session` | Deep multi-turn run; episodic list bounds |
| `memory_forced_speaker` | `pending_forced_speaker` session preseed before Director pick |

**Manifest regression (no API):**

```bash
cd autogen_rp/python
pytest tests/test_progression_simulation_scenarios.py -q
```

---

### 2. Simulation Execution (live LLM)

The **headless runner** drives the same code path as Streamlit: Director selection, character generation, validation, progression enforcement (when enabled), narrator render, continuity / orchestration updates. Character prompts are assembled through **`app_turn_prompting.build_character_turn_prompt`**, including **`build_character_state_context_for_prompt`** for **`state_context`** (same spine as Streamlit; see **`autogen_rp/docs/architecture.md`**).

**Requirements**

- `DEEPSEEK_API_KEY` in the environment
- Shell working directory: `autogen_rp/python`

**Common commands**

```bash
cd autogen_rp/python

# List scenario ids
python scripts/run_scene_simulation_llm.py --list-scenarios

# Run one scenario (prints markdown + structured JSON block)
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --turns 6

# Write structured_eval only to a file (UTF-8 JSON)
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --metrics-out ./runs/treatment.json

# Full audit trail (same JSON audit layout as Streamlit with auditing on)
python scripts/run_scene_simulation_llm.py --scenario strong_user_steer --audit --turns 5

# Baseline comparison: progression enforcement OFF (no gate/retry, no MED→HIGH override)
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --no-progression-enforcement --metrics-out ./runs/baseline.json
```

**Ad-hoc runs** (no scenario file): use `--chars`, `--opening`, `--location`, `--trigger`, `--beat-shift`, `--no-seed-issue` as documented in `scripts/run_scene_simulation_llm.py`.

---

### 3. Deterministic validation lane

Scenario simulation does **not** replace fast regression. Use in parallel:

- **Pytest** (progression contract, gate, retry wiring, orchestration override, turn runner updates, etc.):

  ```bash
  cd autogen_rp/python
  pytest tests/test_progression_enforcement.py tests/test_progression_run_metrics.py tests/test_turn_runner_updates.py tests/test_orchestration_helpers.py -q
  pytest -m "not llm"   # full suite excluding live LLM tests
  ```

- **Headless deterministic scripts** (no LLM; markdown audit to stdout):

  - `python scripts/run_progression_layer_simulation.py` — progression contract / gate / override helpers
  - `python scripts/run_presence_scene_audit.py` — presence harness

These confirm **code-level** behavior; scenarios confirm **model + pipeline** behavior together.

---

### 4. Artifacts, metrics, and evaluation

**What is produced automatically**

- **Markdown report** (stdout): scenario metadata, selector notes, structured moves, chat snippets, progression metrics bullets, and a final **Structured run result (JSON)** block.
- **`structured_eval` JSON** (optional file via `--metrics-out`): stable fields for diffing across runs:

  - `scenario_id`
  - `verdict` / `failure_classification` (when you pass CLI flags; otherwise `null`)
  - `expected_pressure_profile` (from scenario manifest when present; else `null`)
  - `metrics`: first qualifying continuity turn index, progression retry count, failed progression attempts, qualifying vs non-qualifying accepted turns, whether enforcement was on
  - `audit_session_number` / `audit_summary_report_path` when `--audit` was used

**Audit JSON** (with `--audit`): written under `autogen_rp/python/rp_app/data/rp_audits/` (session folders + summary), same mechanism as the Streamlit app with auditing enabled.

#### PASS criteria

**PASS** requires **both**:

1. **Correct structured / system behavior** — contracts (e.g. Q1–Q4 progression delta when enforcement applies), gates, continuity integrity, selection and retry rules behave as intended.
2. **Acceptable scene quality** — nothing **mechanical, forced, or immersion-breaking** in the visible beat (voice, pacing, plausibility). A run that is technically valid but feels like a broken scene is **not** a PASS.

Use **WARN** when mechanics are mostly right but quality is borderline; **FAIL** when either pillar clearly fails.

#### LLM non-determinism

- Identical scenarios can differ run-to-run; compare **structured fields** and audit logs, not prose alone.
- **Do not rely on a single run** for borderline PASS decisions. If behavior looks inconsistent or ambiguous, run the **same scenario 2–3 times** and compare `structured_eval.metrics` and audit outputs before concluding.
- **Versioning:** note model and app revision when archiving benchmark runs (e.g. in commit message or run folder README).

**Manual evaluation (required for release-style sign-off)**

After each run, assign:

- **PASS / FAIL / WARN** (`--verdict` when re-running or edit the saved JSON)
- On **FAIL** or **WARN**, a **failure classification** (`--failure-class`):

  - `contract` — Q1–Q4 / progression delta contract
  - `gate` — gate or threshold (when enforcement triggers or should trigger)
  - `selection` — Director / next-actor selection
  - `retry` — retry behavior (duplicate or progression retry)
  - `continuity` — continuity corruption or unexpected side effects
  - `other`

Example:

```bash
python scripts/run_scene_simulation_llm.py --scenario emotional_loop_2char --metrics-out ./runs/r1.json --verdict WARN --failure-class retry
```

**Checklist and deeper items**

For progression-layer line items, scene-quality notes, and command shortcuts, use:

`autogen_rp/python/tests/Testing TODOs/progression layer testing todo.md`

---

## Progression validation runbook (baseline vs treatment)

Use this loop to validate that **progression enforcement** improves measurable outcomes vs **baseline** (enforcement off), without redesigning the system.

**Scenarios:** `emotional_loop_2char`, `conflict_3char`, `strong_user_steer`

For **each** scenario:

1. Run **baseline** (save metrics + optional audit):

   ```bash
   cd autogen_rp/python
   mkdir -p runs/progression_val
   python scripts/run_scene_simulation_llm.py --scenario <ID> --no-progression-enforcement --audit --metrics-out runs/progression_val/<ID>_baseline.json
   ```

2. Run **treatment** (default enforcement on):

   ```bash
   python scripts/run_scene_simulation_llm.py --scenario <ID> --audit --metrics-out runs/progression_val/<ID>_treatment.json
   ```

   (Adjust `--turns` only if you need parity with the scenario default `max_turns`.)

3. Compare `structured_eval.metrics` (and audits) between the two files; then assign **PASS / FAIL / WARN** and **failure_classification** when not PASS.

**Goal:** Treatment should show **consistent, measurable improvement** (e.g. earlier qualifying deltas, fewer stalled non-qualifying turns, appropriate retries) without systematic quality regressions. Stochasticity: repeat 2–3 times if results disagree.

---

## Usage discipline (from here forward)

- **No major layer change is “done”** without scenario validation relevant to that layer.
- **Scenario runs come before** threshold tuning or new enforcement logic — use evidence from structured outputs and audits, not ad hoc manual runs alone.
- **Manual Streamlit scenes** are for tone, rare edges, and sanity checks **after** scenario validation passes for the change in question.
- **Do not add new metrics or expand this framework** until a **real gap** shows up in practice; avoid premature instrumentation.

---

## Workflow summary

1. Merge or implement features; keep **pytest green** (`-m "not llm"` minimum in CI).
2. Run **relevant scenario(s)** with `--audit` and `--metrics-out` when validating behavior changes.
3. For progression tuning, run **baseline** (`--no-progression-enforcement`) vs **treatment** on the same scenario and compare `structured_eval.metrics`; repeat 2–3 times if borderline.
4. Record **PASS / FAIL / WARN** and **failure class** when the outcome is not a clear PASS.
5. Use **manual scenes** sparingly for tone and edge cases scenarios do not cover.

---

## Constraints

- **Validation phase, not redesign:** failures should drive **targeted** changes only when reproducible and tied to a specific subsystem (contract, gate, selection, retry, continuity) — and **only after** human-approved remediation, not inside the validation pass itself.
- **Answer the question:** *“Did this change actually improve system behavior?”* — use structured_eval + audits; do not expand scope or redesign the framework preemptively.
- **Scenario validation does not modify runtime behavior** — runs **observe** outcomes; they do not change code, scenarios, prompts, or thresholds as part of the run.
- **Triage before any fix:** an unexpected result is classified first ([DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) triage); **no** fix attempts in the same breath as analysis.
- **Comparable runs:** baseline vs treatment and reruns stay apples-to-apples — **no hidden adjustments** between executions unless explicitly documented and intentional.

### Enforced workflow (validation only; hard rule)

1. Run scenario with **`--audit`** and optional **`--metrics-out`**.
2. If the result is unexpected: run **[DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) → Simulation failure triage (layer-aware deep-dive)**.
3. Record **suspected layer**, **verdict** (**legitimate** / **legitimate but undesirable** / **bug** / **ambiguous**), and **minimal repro**.
4. **Stop.** Do not proceed to fixes, reruns with altered conditions, or tuning unless **explicitly instructed** (separate remediation phase).

Full boundary between validation and remediation: **[DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) → Validation vs Remediation Boundary** (under triage).

### Long-session evaluation (`long_session`, natural rerun)

1. **`--scenario long_session`**, **deep simulation** (default), **`--turns 12`**, **`--audit`**, **`--metrics-out`** — let the scene run **naturally** (no artificial exit constraints, no scenario wording edits, no detection tweaks for that run).
2. If a walkout occurs: **triage** the event; classify with the four verdicts; then decide whether the run is **usable** for long-session validation — **do not** auto-rerun to “fix” the outcome.
3. **Usable for long-session evaluation** only if: depth is **~10–12** successful character turns **and** no **critical layer bug** invalidates the run. Otherwise: **classify** the failure; start a **new** run only when directed — **no** automated remediation to salvage the run.

### Validation retry policy (invalid runs)

This is **not** remediation. It only defines **recovery for validation attempts** when a run cannot support the current goal — **no** code, prompt, threshold, or hidden flag changes between attempts unless a human **explicitly** changes the validation plan.

1. **When a run is invalid for the current validation target**
   - **Insufficient depth** — e.g. fewer successful character turns than required for that goal (long-session arc, retry stress, etc.).
   - **Confirmed bug** — triage **bug**; the run must **not** be used as clean evidence for production-readiness until addressed in a **separate** remediation phase.
   - **Critical ambiguity** — triage **ambiguous**; outcome cannot be interpreted vs baseline/treatment or vs the question under test.

2. **Retry rule**
   - **Triage first**; record **suspected layer**, **verdict**, and **why** the run is invalid.
   - Only then may a human **manually** start a **new** run with the **same** scenario and flags (comparable) unless the plan is deliberately updated.

3. **Retry limit**
   - **At most 2–3 retries per scenario** for the **same validation goal** (same question / comparison), **in addition to** the first attempt. Further attempts require **rescoping** or a **different** scenario (see below).

4. **Stop condition**
   - If repeated runs fail for the **same substantive, repeating reason** (documented in triage), **stop** retrying that scenario for that goal until something changes (scenario design, validation target, or post-remediation code).

5. **Next action after stop**
   - Use a **different scenario** that still targets the layer or hypothesis.
   - **Manually redesign** the scenario (human-authored manifest change — test-artifact work, distinct from runtime remediation).
   - **Re-scope** the validation target (narrow what counts as success for this phase).

### When a run “looks wrong” (triage pointer)

Before changing code, use **[DEBUGGING_GUIDE.md](./DEBUGGING_GUIDE.md) → Simulation failure triage (layer-aware deep-dive)**. Evidence order, layer labels, and verdicts are defined there; **remediation** is separate and human-directed.

---

## Latest validation status (checkpoint)

**Progression layer (v1):** declared **validated** — `autogen_rp/python/tests/Testing TODOs/progression layer validation status v1.md`.

Written assessment, limitations, and historical phase notes also live in:

`autogen_rp/python/tests/Testing TODOs/progression layer testing todo.md` → sections **“Validation checkpoint — initial LLM runs”**, **Phase 2**, **Phase 2b**, etc.

### Deep simulation (headless)

By default, **`--scenario`** runs use **deep simulation**: the runner honors scenario **`max_turns`** (or `--turns`) for how many **successful character turns** to allow in **one** simulated user message, and the **same cast may speak multiple times** (unlike Streamlit’s one-reply-per-bot cap for a single user round). Use **`--no-deep-simulation-turns`** to match that short UI-style cap. Ad-hoc mode (`--chars`, no `--scenario`) stays short-cap unless you pass **`--deep-simulation-turns`**.
