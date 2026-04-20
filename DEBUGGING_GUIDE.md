# RP debugging guide

How to **approach problems** in the Holy Grail RP runtime without fixing the wrong layer. Product and layers: [Holy Grail PRD.md](./Holy%20Grail%20PRD.md), [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md). **Where to open code first:** [MODULE_INDEX.md](./MODULE_INDEX.md) (symptom table; modules live under `autogen_rp/python/rp_app/`). **On-disk data:** [autogen_rp/docs/rp-data-layout.md](./autogen_rp/docs/rp-data-layout.md).

---

## Golden rules

1. **Continuity and orchestration before Director prompts** — If the wrong person speaks or state feels wrong, inspect structured state and orchestration before editing Director instructions (`prompt_builders.py` / `app_turn_director.py`).
2. **Do not use prompts as long-term memory** — Truth for scenes/issues/events lives in **continuity** (`continuity_manager.py`), not in growing hidden transcripts.
3. **Validation is not continuity** — Validators reject or shape outputs; they do not author “what happened.” Fix extractors/updaters in continuity if fiction state is wrong.
4. **`must_remain` is structural presence** — Not “must speak every turn.” Presence bugs: `response_validation_presence.py`, templates, then semantics overrides if needed.

---

## Suggested diagnosis order (runtime)

Aligned with `autogen_rp/docs/architecture.md` and `autogen_rp/docs/audit-workflows.md`:

1. **Continuity extraction and state** — Are events, issues, and scene snapshot correct after the turn? (`continuity_manager.py`, `continuity_*_helpers.py`)
2. **Perception / audibility** (when the bug is knowledge boundaries, whispers, or “who saw that line”) — `perception_audibility.py`, `app_turn_prompting.py`, `prompt_builders.py`; confirm with per-character audit `_full.json` prompts, not `_narrative.json` alone
3. **Scene grounding + binding** — Does `scene_grounding` reflect continuity (settled facts present, not stale, not empty when extraction promoted)? For **character** turns, does `_full.json` include **BINDING CONSTRAINTS** when binding categories are active? (`scene_grounding.py`, `app_turn_prompting.py`, `prompt_builders.py`)
4. **Evidence / authority wording** — If the issue is **fabricated specifics** in clinical or “noted” voice (not continuity truth), check the static **EVIDENCE & AUTHORITY DISCIPLINE** block in `prompt_builders.py` and the model output; still verify perception and grounding first so you are not debugging the wrong layer
5. **Orchestration state** — Spotlight, forced speaker, continuation override (`orchestration_helpers.py`, `st.session_state` keys used in `app_turn_director.py`)
6. **Summaries / retrieval windows** — What the prompt actually sees (`summary_audit_helpers.py`, `prompt_builders.py` only after earlier layers look sane)
7. **Validation boundaries** — Parsing, presence, drift, selection (`response_validation_*.py`); turn-selection preemption checks respect `decision["source"] == "fallback"`
8. **Memory layer (prompt read path)** — Episodic sections in character prompts: `memory_layer/retrieval.py` + `build_character_state_context_for_prompt`; production `state_context` is built only in `app_turn_prompting` (see `autogen_rp/docs/architecture.md`)
9. **Director** — Selection policy and prompts when evidence points here
10. **Narrator** — Prose polish; dialogue must stay verbatim (`app_turn_rendering.py`)

---

## Simulation failure triage (layer-aware deep-dive)

Use this when a **headless scenario run** or **Streamlit session** “looks wrong” (FAIL/WARN, bad prose, collapsed cast, stuck loop) and you are deciding whether to **change code** and **which subsystem** owns the fix. It is the default path between **“simulation looked wrong”** and **“open the right file.”** Headless runs: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md); audit layout: [autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md](./autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md).

### Workflow

1. Reproduce with **`--audit`** (and **`--metrics-out`** if you want a frozen `structured_eval`). Note scenario id, baseline vs treatment, deep vs `--no-deep-simulation-turns` if relevant. If the run used **`--user-trigger-schedule`**, use **`effective_user_trigger`** on **full** per-turn audit JSON to see which simulated user line applied each turn (see [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) for JSON shape, precedence, and validation).
2. Pick **one primary Layer** first (canonical list below; full definitions in [governance/rp-app/issue-tracking-workflow.md](./governance/rp-app/issue-tracking-workflow.md) **§F**). Do not spread the investigation across Layers until the evidence chain is clear.
3. Walk **evidence order** once, top to bottom; stop when you can name what **committed** the bad state.
4. Produce **Layer**, **verdict**, and **minimal repro** (scenario id, audit session folder, turn index if known)—same fields as mandatory GitHub evidence in **§D** when filing.
5. **Stop** — validation and triage end here (see **Validation vs Remediation Boundary** below). Do not implement fixes or alter runs in the same pass unless a human **explicitly** directs remediation.

### Validation vs Remediation Boundary

- The validation path **observes, classifies, and reports**; it **stops** at **classification + minimal repro**.
- **No automatic remediation:** do not change code, scenarios, prompts, thresholds, or runtime behavior while acting as validator.
- **All fixes** require **explicit human approval** and are **manually implemented** in a separate remediation phase.
- Do not **tune or “try fixes”** automatically after triage (no drive-by patches, prompt edits, or scenario tweaks to “see if the run improves”).
- Do not **rerun with altered conditions** (different flags, edited JSON, local hacks) unless **explicitly instructed**; comparability of runs matters.
- During **validation phases**, do not optimize behavior or “improve outcomes” — analyze, attribute to layer, document, then **stop**.
- In **remediation** (after approval), changes should **target the triaged layer** unless new evidence overturns the prior classification.
- **Invalid run / validation retries** (when to try another run, how many times, when to stop — **not** auto-fix): [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) → **Validation retry policy (invalid runs)**.

### Evidence order (strict)

1. **Structured move** — `action`, `dialogue`, `motivation`, `presence_changes`, raw character JSON (source of truth; not inferred from prose alone).
2. **Consequences / classification** — What tags fired (`exit`, etc.) and how they attach to the move (`continuity_consequence_classifier`, `scene_exit_detection.detect_exit_from_scene`; continuity applies rules in `continuity_manager.py`, e.g. canonical exit handling). **`turn_metadata["consequences"]` / audit `metadata.consequences` is classifier-only:** if the list is **empty**, do **not** stop—explicitly check **`continuity_event`** (e.g. `context_snapshot.continuity_event` / committed event fields), **`issue_updates`** (`metadata.issue_updates`), and allowlisted **`scene_state_updates`** on the structured move. Empty **`consequences`** does **not** imply no structural change; progression can still satisfy **Q2** / **Q4** with an empty **Q1** list (`progression_enforcement.py`; **`ARCHITECTURE.md`** — classifier lane vs continuity commits). On character **`metadata.audit_v2`**, **`char_masked_progression_strict`** (`payload.observation` / `signals`) summarizes strict-tier **masked progression** for triage only—**not** continuity truth or a defect (**#73**, **`AUDIT_DOCUMENTATION.md`**).
3. **Continuity snapshot** — After the suspect turn: `present_characters`, `offstage_characters`, `character_presence_status`, active issues/events as needed (audit + `continuity_manager` / `SceneState`).
4. **Selector / Director** — Orchestration notes, overrides, `selector_decisions` / audit selection stages (`orchestration_helpers.py`, `app_turn_director.py`, `response_validation_selection.py`).
5. **Narrator / rendered chat last** — Confirms presentation and model tone; **do not** treat as proof of what continuity believed.

### Primary Layer (pick one to start)

Use [MODULE_INDEX.md](./MODULE_INDEX.md) for file-level routing. The **Layer** value must match [governance/rp-app/issue-tracking-workflow.md](./governance/rp-app/issue-tracking-workflow.md) **§F** (file GitHub Issues with the same token). **Orchestration vs response_validation:** wrong **who acts next** → **`orchestration`**; wrong **validity of a produced move** (parse, presence, duplicate content, drift on character/narrator payload) → **`response_validation`**.

| Layer | Typical symptoms | First code to inspect |
|-------|------------------|------------------------|
| `consequence_classification` | Consequence list contradicts plain reading of structured move | `continuity_consequence_classifier.py`, `scene_exit_detection.py` (classification from move) |
| `continuity_state` | Wrong issues/events/scene fields **after** a turn (committed truth) | `continuity_manager.py`, `continuity_*_helpers.py`, `turn_runner_updates.py` |
| `progression` | Retry / gate / Q1–Q4 delta behavior | `progression_enforcement.py`, `turn_runner_turn.py` |
| `orchestration` | Wrong next actor, pool, address, continuation | `app_turn_director.py`, `orchestration_helpers.py`, `response_validation_selection.py`, `semantic_validation.py` |
| `response_validation` | Invalid/rejected character or narrator **payload** (presence, duplicate, parse, drift) | `response_validation_parsing.py`, `response_validation_content.py`, `response_validation_presence.py`, `response_validation_drift.py` |
| `grounding` | SETTLED SCENE FACTS / BINDING CONSTRAINTS wrong vs continuity | `scene_grounding.py`, `app_turn_prompting.py`, `prompt_builders.py` |
| `perception` | Wrong knowledge boundary in prompts (who sees dialogue/rendered text) | `perception_audibility.py`, `app_turn_prompting.py`, `prompt_builders.py` |
| `memory` | Episodic or retrieved bundle wrong given continuity | `memory_layer/`, `episodic_memory_*.py`, `retrieved_context_select.py` |
| `rendering` | Prose garble, voice, dialogue not verbatim in rendered output | `app_turn_rendering.py`, narrator prompts |
| `audit_simulation` | Wrong or missing audit artifacts, harness, metrics | `headless_scene_simulation.py`, audit writers, scenario CLI |
| `application_infrastructure` | Encoding, Streamlit shell, session I/O, loader/path mechanics | `app.py`, session lifecycle, env/paths |
| `other` | Only per **§F** (`other`): non-runtime process/tooling, or **`investigating`** with target Layer hypothesis + justification | [governance/rp-app/issue-tracking-workflow.md](./governance/rp-app/issue-tracking-workflow.md) **§F** |

### Verdict (record one)

- **legitimate** — State change matches the structured move and rules; scene behaved as designed.
- **legitimate but undesirable** — Rules and classifiers behaved as implemented, but the outcome is a **design or scenario weakness** (e.g. trigger phrasing, cast size, template pressure). Map to GitHub **Type** **`quality`** or **`design_gap`** when filing; fix may be scenario/template/product rule, not a random prompt tweak.
- **bug** — Implementation contradicts PRD/architecture expectation; fix belongs in the **primary Layer** above when filing (**Type** **`bug`**).
- **ambiguous** — Not enough evidence in one pass; re-run, add audit session, or isolate turn before coding.

### Success criteria

- There is a **default path** from “simulation looked wrong” to **Layer-labeled** investigation **before** any **approved** code change.
- Oddities are **labeled by Layer** before fixes; **`progression`** is not tuned for **`response_validation`**, **`continuity_state`**, **`orchestration`**, or **`application_infrastructure`** bugs unless triage (then human-directed remediation) says so.
- Repros stay **small** (scenario + audit session + optional `structured_eval` path).
- **Triage output is complete** when **Layer**, **verdict**, and **minimal repro** are recorded and the validation pass **stops** — implementation is out of band.

---

## By problem type

### Turn selection issues

- **Who speaks next** — `orchestration_helpers.py` (address / continuation / caps), `app_turn_director.py` (Director call and overrides; **v1:** continuation C2 skip when last spotlight matches continuation actor — see `autogen_rp/python/RP_SETUP_TODO.md` §I), `response_validation_selection.py`, then `semantic_validation.py` for reconciliation. Audits / sim metrics: `selection_attribution`, `continuation_override_skipped_c2`.
- **Director ignores context** — Check what **structured** inputs the prompt receives (`prompt_builders.py`, continuity snapshot helpers), not only the Director system text.

### Character drift (voice, tone, anchors)

- **Post-move checks** — `response_validation_drift.py`
- **Anchor source** — `character_state_model.py`, JSON cards under `python/data/autogen_characters/`
- **Drift false positives** — Tune checks in `response_validation_drift.py`, not Narrator prose prompts first.

### Presence bugs (`must_remain`, exits, absence)

- **Deterministic rules** — `response_validation_presence.py`, `scene_exit_detection.py` (continuity), template constraints in `scene_template.py`
- **Semantic override** — `semantic_validation.py`, `should_override_presence_rejection` path in `turn_runner_turn.py` (only after understanding deterministic path)

### Duplicate dialogue / repeated outputs

- **Detection** — `response_validation_content.py` (`is_duplicate_dialogue`, `is_duplicate_content`)
- **Retry behavior** — `turn_runner_turn.py` (duplicate retry branch)
- **Do not** “fix” with Narrator instructions until duplicate rejection logic is understood.

### Progression enforcement (structural delta under stall)

When **beat-shift is active** or **progression pressure is high**, a character turn must produce a **qualifying continuity delta** after `process_turn` (consequences / issue movement / arrival-exit / bounded `scene_state_updates`), or the runtime **retries once** before failing the turn. Logic: `progression_enforcement.py`; pipeline: `process_turn` runs **before** narrator/chat in `turn_runner_turn.py`, with snapshot/restore on failed check. **Q3 (presence)** uses continuity `turn_meta["consequences"]` only (same signal orchestration mirrors later), not `orchestration_state` alone.

### Knowledge leaks / wrong “who knows what”

- **Prompt assembly first** — `perception_audibility.py` (structured `move` + filtering), then `app_turn_prompting.py` / `prompt_builders.py`; verify **each** character’s Director/character `_full.json` `input_messages`, not the shared `_narrative.json` dialogue column alone
- **Continuity propagation** — `continuity_knowledge_helpers.py`, `continuity_manager.py` (`PublicEvent` knowability, interpretations)
- **Validation** — Knowledge-related checks live alongside other validators; boundary truth combines continuity with perception filtering (future: [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md))

### Persistence / reload issues

- **Session / continuity blobs** — `session_manager.py`, `session_lifecycle_save.py`, `session_lifecycle_load.py`, `app_bootstrap.py`
- **Scene state fields** — check `SceneState` and `ContinuityManager.to_dict()` / `.from_dict()` paths before blaming prompt assembly.

### Scene start / first-round simulated user line (UI vs headless)

- **Canonical fresh-scene bootstrap (GitHub #83)** — `scene_start_bootstrap.py`, `app_state_continuity.py` (`restore_or_initialize_continuity_manager`); UI entry `scene_lifecycle_start.py`; headless prep `headless_scene_simulation.py` (`prepare_headless_session`).
- **Scenario contract** — `startup_trigger_mode` + `effective_round1_trigger_text_headless` in `progression_simulation_scenarios.py`; regression coverage `tests/test_issue83_scene_start_contract.py`.

### Settled sleeping assignment re-litigation

- **Continuity-owned resolved outcome first** — inspect `resolved_outcome_registry.py`, `resolved_outcome_engine.py`, `continuity_resolved_outcomes.py`, `continuity_manager.py`, and `turn_metadata_by_index[*]["resolved_outcomes"]["sleeping_surface"]` before editing prompt wording. Identical-value reassertion surfaces as `no_op_existing_value`.
- **Grounding projection second** — confirm `scene_grounding.py` reflects the active `assignment:sleeping_surface` outcome into SETTLED SCENE FACTS.
- **Template slots / move field** — verify the scene exposes bounded `sleeping_surface_slots` and the structured move includes `scene_state_updates.sleeping_surface_assignment` only when the beat truly settles the assignment. In headless/simulation runs, those slots come from the scene template: set scenario `scene_template_id`, and if the template has required roles, add `scene_template_role_assignments` (see `SCENARIO_VALIDATION_FRAMEWORK.md`).

### Settled housing-call re-litigation

- **Continuity-owned resolved outcome first** — inspect `resolved_outcome_registry.py`, `resolved_outcome_engine.py`, `continuity_resolved_outcomes.py`, `continuity_manager.py`, and `turn_metadata_by_index[*]["resolved_outcomes"]["housing_call"]` before editing prompt wording. Identical-value repetition surfaces as `no_op_existing_value`.
- **Grounding projection second** — confirm `scene_grounding.py` reflects the active `communication_state:housing_call` outcome into SETTLED SCENE FACTS.
- **Move field discipline** — verify structured output uses only `scene_state_updates.housing_call_outcome` with terminal `status` values `completed` or `failed`, never planning or in-progress chatter.
- **No lexical emission** — `compute_grounding_markers` does **not** add `communication_state:housing_call` on new turns; older sessions may still carry that marker on saved `PublicEvent` rows, which rebuild can read without conflicting with an active resolved outcome for the same slot.

### Audit output / regression analysis

- **Layout and file meanings** — `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`
- **Continuity audit surfaces (Issue #79, not #59 runtime authority)** — Per-turn **`metadata.ctar`**, **`context_snapshot.scene_state_after`**, **`metadata.excursion_audit_digest_v1`**, and **`metadata.continuity_audit_origin`** are for inspection; bypass classification for non-pipeline commits rolls up under **`continuity_observability_summary_v1.session_audit_origin`** on **`_audit_summary.json`** when that summary block is present. For committed truth, use **`ContinuityManager`** / **`turn_metadata_by_index`** (including **`continuity_mutation_resolution`** on the pipeline path), not audit JSON alone.
- **`_audit_summary.json` — continuity observability rollup (Issue #79):** **`continuity_observability_summary_v1`** is emitted only when **`write_summary_report`** receives a **`ContinuityManager`** (continuity-backed rollup available). When it does not, **`continuity_observability_status_v1`** is emitted instead (**`status`**: **`unavailable`**, **`reason`**: **`continuity_manager_not_provided`** — the current canonical reason). The two top-level keys are mutually exclusive. **`continuity_observability_status_v1`** explains unavailability of the rollup; it is **not** a failure verdict on the session or audit path.
- **`scene_eval_v2` / narrator↔character joins** — If linkage fails or looks wrong, check **`context_snapshot.continuity_turn_index`** on **both** rows first (primary structural join). **Missing `continuity_event.event_id` is not a failure** when indices match; `event_id` is **optional** and used only as **legacy** fallback when top-level **`continuity_turn_index`** is absent on one or both sides.
- **Workflow** — `autogen_rp/docs/audit-workflows.md`
- **Writers** — `audit_logger*.py`

---

## Layer responsibility (who owns what)

| Layer | Owns |
|-------|------|
| **Ingestion** (future) | Source extraction, graph/vector stores — not live turn loop |
| **Packaging** (future) | Merging packets + retrieved context — not replacing continuity truth |
| **RP runtime (`rp_app`)** | Director, orchestration, agents, Narrator, **continuity**, validation, session/audit I/O |

---

## Related

- [GLOSSARY.md](./GLOSSARY.md)
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — future seam; do not implement retrieval as authoritative state
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) — headless **authored retrieval OFF/ON** (`RP_RETRIEVED_CONTEXT_INDEX`, `--retrieved-context-index`) and **`structured_eval.retrieval_session`**; **per-turn user trigger schedule** (`--user-trigger-schedule`, JSON, precedence, orchestration turn index)
- [autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md](./autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md) — **`retrieval_summary`** (per turn), **`retrieval_session`** in `_audit_summary` (Streamlit + headless merge); **`effective_user_trigger`** (full audits only; schedule overrides are headless harness-only); **Issue #79** continuity surfaces (**`metadata.ctar`**, **`scene_state_after`**, **`continuity_observability_summary_v1`** or **`continuity_observability_status_v1`**)
