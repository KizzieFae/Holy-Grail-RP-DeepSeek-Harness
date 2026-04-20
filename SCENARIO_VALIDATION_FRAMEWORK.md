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
| `willow_dorm_binding_stress` | Dorm logistics + binding-fact stress (Willow / sleeping surface enforcement) |
| `arkham_multi_character_stress` | Nine-character clinical/security/patient corridor stress (perimeter-alarm rumor) |
| `arkham_multi_character_stress_long` | Same cast as `arkham_multi_character_stress`; higher `max_turns` / extended premise for staff–patient cycling |
| `headless_template_retrieval_smoke` | Minimal Harley/Magpie run; `scene_template_id` for template-linked authored retrieval checks |
| `operational_baseline_3char_cafeteria` | **Accepted retrieval baseline** cast (Harley, Ivy, Magpie) + cafeteria template for standard OFF vs ON comparisons |

**Optional scenario fields**

- **`scene_template_id`**: When set, headless prep loads the matching JSON under `python/data/scene_templates/` and applies **template-derived** fields onto `ContinuityManager.scene_state` (at minimum `sleeping_surface_slots` / `location_entry_slots` / `premise` / `scene_template_id`). Use for scenarios where template contract fields must match Streamlit-style setup. Omit for character-only expectations or casts outside the indexed templates.
- **`scene_template_role_assignments`**: **Required** when **`scene_template_id`** is set (Issue #80). Object mapping every **`character_card_ids`** entry → template **`role_name`** (same vocabulary as the template’s `role_slots`), validated at scenario load. Exactly one character must map to the template’s **`anchor_role_name`**. Optional **`anchor_role_name`** may mirror the template (must match exactly) or be omitted (inherit). Headless prep uses the same **`resolve_scene_template_setup`** path as the UI.

**Manifest regression (no API):**

```bash
cd autogen_rp/python
pytest tests/test_progression_simulation_scenarios.py -q
```

---

### 2. Simulation Execution (live LLM)

The **headless runner** drives the same code path as Streamlit: Director selection, character generation, validation, progression enforcement (when enabled), narrator render, continuity / orchestration updates. Character prompts are assembled through **`app_turn_prompting.build_character_turn_prompt`**, including **`build_character_state_context_for_prompt`** for **`state_context`** (same spine as Streamlit; see **`autogen_rp/docs/architecture.md`**). **Continuity scope:** scenario runs validate the **current** pipeline and scenarios in this matrix; they do **not** by themselves prove **full** Runtime Continuity Contract delivery (**GitHub #77**). **Slice A**-scoped foundation is validated separately; **#33 / #34**-class spatial/offscreen-merge behavior and deferred layers are tracked in **#81**.

**Requirements**

- `DEEPSEEK_API_KEY` in the environment **of the Python process** that runs `scripts/run_scene_simulation_llm.py` (set it in that shell before invoking Python, or inject it via your IDE/CI/automation config). Variables that exist only in a different interactive session or parent profile are **not** inherited—this is normal OS process isolation, not something the scenario JSON or user-trigger schedule changes.
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

### Optional offline fact-track (post-processing, GitHub #62)

After a run that used **`--audit`**, you may attach an explicit **`fact_spec.v1`** probe in the **same** `run_scene_simulation_llm.py` invocation (default **off** — omit both flags):

| Flag | Required | Role |
|------|----------|------|
| **`--fact-spec PATH`** | Requires **`--audit`** | Load JSON (`fact_spec.v1`); no implicit default spec. |
| **`--fact-track-out PATH`** | Optional; requires **`--fact-spec`** | Write the companion JSON to this path instead of the default under the session directory. |

**Output:** A **companion** UTF-8 JSON file (`fact_track__<probe_id>__<sha-prefix>.json` by default) next to other session artifacts. It is **not** merged into **`_audit_summary.json`** in v1 and is **not** part of the base audit logger contract.

**Semantics:** **Observational / offline only** — same **#59** authority boundary as `AUDIT_DOCUMENTATION.md` → **Offline fact tracking** (not runtime; not on the runtime use allowlist). Deterministic; no LLM in the fact-track path.

**Non-CLI orchestration:** Call **`run_fact_track_postprocess`** from `rp_app/audit_fact_tracking.py` with a resolved session directory and loaded spec dict (same behavior as the CLI adapter).

**Example:**

```bash
cd autogen_rp/python
python scripts/run_scene_simulation_llm.py --scenario arrival_setup --audit --turns 1 --fact-spec ./path/to/probe.json
```

**Console captures (stdout / tee)** — When saving the printed markdown audit stream to a file (`>`, `Tee-Object`, etc.), **write under `autogen_rp/python`**, e.g. `./runs/<name>.log` or `./validation_runs/<name>.log`. **Do not** redirect output to the **Holy Grail repository root** (the folder that contains `Holy Grail PRD.md` and `README.md`); that mixes ad-hoc run transcripts with foundational documents. With `--audit`, authoritative JSON still lands under `rp_app/data/rp_audits/`. The repo root [`.gitignore`](./.gitignore) ignores patterns such as `/*_run*_audit.log`, but ignored files still clutter the working tree if created there.

### Authored retrieval (standard evaluation mode)

Retrieval activation is **only** via environment variable `RP_RETRIEVED_CONTEXT_INDEX` (compiled JSON path). The headless runner can set it for a single process:

| Goal | Command pattern |
|------|-----------------|
| **Retrieval OFF** | Unset the variable, or pass `--retrieved-context-index` with no value (empty index). |
| **Retrieval ON (accepted baseline)** | `--retrieved-context-index data/retrieval/compiled/operational_pilot_v3.json` (from `autogen_rp/python` cwd). |
| **Leave parent shell unchanged** | Omit `--retrieved-context-index` entirely. |

Example A/B pair (same scenario, different retrieval):

```bash
cd autogen_rp/python
python scripts/run_scene_simulation_llm.py --scenario operational_baseline_3char_cafeteria --audit --turns 4 --metrics-out ./runs/caf_OFF.json --retrieved-context-index
python scripts/run_scene_simulation_llm.py --scenario operational_baseline_3char_cafeteria --audit --turns 4 --metrics-out ./runs/caf_ON.json --retrieved-context-index data/retrieval/compiled/operational_pilot_v3.json
```

**Verification**

- **Structured output:** `structured_eval.retrieval_session` includes `retrieval_mode` (`"off"` \| `"on"`), `retrieval_index_path`, `retrieval_verified_active`, and optional `retrieval_index_fingerprint`.
- **Strict check (headless):** If retrieval is ON **and** the scene has `scene_template_id`, the run **fails** if no character turn produced a non-empty retrieved bundle (avoids silent misconfiguration).
- **Per-turn audits:** Character `*_full.json` metadata may include `retrieval_summary` (`retrieved_block_present`, counts, capped `retrieved_source_refs`) — no full retrieved text.
- **`_audit_summary.json`:** After a **headless** `run_headless_llm_scene` completes, a top-level **`retrieval_session`** object is **merged** into `_audit_summary.json` when that file exists (post–summary refresh). **Streamlit** sessions with auditing on still get **per-turn** `metadata.retrieval_summary` on character entries when applicable, but **`retrieval_session` is not written into `_audit_summary.json` on the UI path today** — use headless `--audit` runs or **`structured_eval.retrieval_session`** from the simulation CLI for the run-level block.

**Default scenario set for OFF/ON comparisons** (operational index): `headless_template_retrieval_smoke`, `operational_baseline_3char_cafeteria`, and optionally `arkham_multi_character_stress` / `_long` (large cast; template id set for cafeteria template). Scenarios such as `emotional_loop_2char` remain valid for non-indexed casts (retrieval ON may still be neutral/empty for those cards).

**Ad-hoc runs** (no scenario file): use `--chars`, `--opening`, `--location`, `--trigger`, `--beat-shift`, `--no-seed-issue`, and optionally `--user-trigger-schedule` as documented in `scripts/run_scene_simulation_llm.py`.

### Per-turn user trigger schedule (headless simulation harness only)

Optional **`--user-trigger-schedule PATH`** on `scripts/run_scene_simulation_llm.py` loads a JSON file so **validation / simulation runs** can use **different simulated user lines on different orchestration turns**—for one-off establishment, probes, or scripted inputs—**without** repeating the same `--trigger` every turn or editing scenario JSON between runs. This path is **headless CLI only**; it is **not** a Streamlit or live product/runtime feature, and it does **not** extend scenario schema or continuity persistence.

**JSON shape** (single object):

- Optional **`default_trigger`**: non-empty string.
- Optional **`by_orchestration_turn`**: object mapping **orchestration turn index** → non-empty string. Keys must be JSON integers or stringified integers **≥ 1**, **≤** the run’s effective turn cap (the same value as `--turns` when set, otherwise scenario `max_turns` or ad-hoc default). Duplicate keys are rejected. Any other top-level key is rejected.

**Example:**

```json
{
  "default_trigger": "Neutral line for turns not listed in by_orchestration_turn.",
  "by_orchestration_turn": {
    "1": "A sudden magical surge transforms Ayame into an anthro fox—ears, tail, and posture shift visibly.",
    "12": "Celina, you notice her tail flick—ask her directly about still being in fox form."
  }
}
```

**Precedence** for orchestration turn *n*: entry in **`by_orchestration_turn`** for *n* (if present) → else **`--trigger`** if the CLI user **passed** `--trigger` → else **`default_trigger`** if present → else built-in text (scenario **`trigger_text`** or ad-hoc default).

**Validation:** The file is read and validated **before** `prepare_headless_session` and **before any LLM calls**. Invalid JSON, unknown keys, empty strings, out-of-range turn indices, or duplicate keys produce a clear error and the process exits without starting the run.

**Orchestration turn index:** The **1-based** accepted character-turn counter used in the production turn loop and recorded as audit **`turn_number`** for that beat (aligned with per-turn audit artifacts for that turn). Initial round prep (e.g. beat-shift activation and first application of the user line to offstage context) uses the resolver at turn **1** only.

**Audits:** Per-turn **full** audit JSON includes top-level **`effective_user_trigger`** for the string actually used that turn. **Light** audit summaries do **not** include this field—use **`*_full.json`** when correlating probe lines to behavior. See **`autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`**.

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
  - `metrics`: first qualifying continuity turn index, progression retry count, failed progression attempts, qualifying vs non-qualifying accepted turns, whether enforcement was on; when the sim records selection events, **`selection_attribution_summary`** (hard routes, progression-override applications, fairness rotations, attribution-chain counts)
  - `audit_session_number` / `audit_summary_report_path` when `--audit` was used
  - **`retrieval_session`** (headless simulation): `retrieval_mode` (`off` / `on`), `retrieval_index_path`, `retrieval_verified_active`, optional `retrieval_index_fingerprint` — see *Authored retrieval* above

**Selection attribution (baseline v1):** Director audit metadata may include **`selection_attribution`** with **`continuation_override_skipped_c2: true`** when the continuation override was eligible but skipped because the last spotlight speaker already matched the continuation actor (see `autogen_rp/python/RP_SETUP_TODO.md` Phase 0 §I). On normal quality runs, optionally note how often C2 fires and whether continuation / override behavior feels improved — no separate C2-only validation phase required.

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

### Post–GitHub #24 prompt-integrity validation wave (closed **2026-04-07**)

Headless runs from `autogen_rp/python` with **`--audit`** and **`--metrics-out`** (`validation_runs/plan_execution/*.json`). Audit sessions **`session_388`**–**`session_393`**.

| Scenario | Turns (capped) | Audit session |
|----------|----------------|---------------|
| `willow_dorm_binding_stress` | 7 | 388 |
| `conflict_3char` | 7 | 389 |
| `emotional_loop_2char` (×2) | 6 each | 390, 391 |
| `arkham_multi_character_stress_long` | 11 | 392 |
| `long_session` | 12 | 393 |

**Outcomes (phase close):**

- **#24 (prompt integrity):** Sampled character `*_full.json` prompts — **no regression** (actor exclusion from **OTHER PRESENT CHARACTERS**; **CAST ROLE MAP** id/display dedupe). See **`AUDIT_DOCUMENTATION.md`** (cast roster verification) and GitHub **#24**.
- **Classifier gate:** `pytest tests/test_continuity_consequence_classifier.py tests/test_progression_enforcement.py` — **51 passed** (run at close of wave).
- **Exit vs presence:** **`long_session`** provided **exit/expulsion language** stimulus; `present_characters_after` in narrative remained consistent with both characters on-stage for checked turns — **pass** for this wave (not inconclusive).
- **Progression:** **No** `progression_retries` in structured metrics for these runs; **watch** — one **non_qualifying** accepted turn on **`emotional_loop_2char` run 2** (run 1 all qualifying). Lack of retries does **not** prove enforcement-boundary completeness.
- **#1 (identity bleed):** **Not reproduced** in this wave; issue **stays open** — absence of reproduction is not verification.
- **Director/orchestration:** Advisory noise (semantic turn_selection, addressee mismatch notes, fairness rotation) observed in some runs — **not** filed as separate issues for this phase; treat as **watch** in issue comments / future triage if recurring. **Post-wave code:** progression-gated **addressee alignment** (`semantic_validation` + `app_turn_director`) and mixed-transition **`required_next_step` plateau refresh** (`continuity_issue_helpers`) are documented in **`autogen_rp/python/rp_app/ARCHITECTURE.md`**; validated-vs-final pick divergence remains **GitHub #25**.

### Deep simulation (headless)

By default, **`--scenario`** runs use **deep simulation**: the runner honors scenario **`max_turns`** (or `--turns`) for how many **successful character turns** to allow in **one** simulated user message, and the **same cast may speak multiple times** (unlike Streamlit’s one-reply-per-bot cap for a single user round). Use **`--no-deep-simulation-turns`** to match that short UI-style cap. Ad-hoc mode (`--chars`, no `--scenario`) stays short-cap unless you pass **`--deep-simulation-turns`**.
