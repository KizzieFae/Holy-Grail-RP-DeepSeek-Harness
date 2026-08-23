# RP debugging guide

How to **approach problems** in Holy Grail RP without fixing the wrong layer. Product and layers: [governance/sources/holy-grail-prd.md](./governance/sources/holy-grail-prd.md), [governance/sources/architecture-overview.md](./governance/sources/architecture-overview.md). **Where to open code first:** [MODULE_INDEX.md](./MODULE_INDEX.md). **On-disk data:** [docs/rp-data-layout.md](./docs/rp-data-layout.md). Implementation tree: [v2/README.md](./v2/README.md).

---

## Golden rules

1. **Continuity and speaker selection before Director prompts** — If the wrong person speaks or state feels wrong, inspect committed continuity and Host/DSH selection before editing Director prompt text (`prompt_builders.py` / Host projector).
2. **Do not use prompts as long-term memory** — Truth for scenes/issues/events lives in **continuity** (`continuity_manager.py`), committed through the Domain Host, not in growing hidden transcripts.
3. **Validation is not continuity** — Validators reject or shape outputs; they do not author “what happened.” Fix extractors/updaters in continuity if fiction state is wrong.
4. **`must_remain` is structural presence** — Not “must speak every turn.” Presence bugs: `response_validation_presence.py`, templates, then Host/DSH selection if the wrong actor was eligible.

---

## Suggested diagnosis order (runtime)

Aligned with `docs/architecture.md` and `docs/audit-workflows.md`:

1. **Continuity extraction and state** — Are events, issues, and scene snapshot correct after the turn? (`continuity_manager.py`, `continuity_*` helpers; Host `commit_move`)
2. **Perception / audibility** (knowledge boundaries, whispers, “who saw that line”) — `perception_audibility.py`, Host `continuity_context_projector.py`, `prompt_builders.py`; confirm with per-role prompt manifests / traces, not presentation text alone
3. **Scene grounding + binding** — Does `scene_grounding` reflect continuity? For character turns, do binding constraints appear when those categories are active? (`scene_grounding.py`, Host projector, `prompt_builders.py`)
4. **Evidence / authority wording** — If the issue is **fabricated specifics** in clinical or “noted” voice (not continuity truth), check the static **EVIDENCE & AUTHORITY DISCIPLINE** block in `prompt_builders.py` and the model output; still verify perception and grounding first
5. **Speaker selection** — Eligibility, participation, Director decision (`participation_policy.py`, Host eligible-actors APIs, DSH `director-phase.mjs` / `hg-round-orchestrator`)
6. **Summaries / retrieval windows** — What the prompt actually sees (Host projector + `memory_layer/retrieval.py` / Host retrieval services)
7. **Validation boundaries** — Parsing, presence, drift, selection (`response_validation_*.py`); Host `validate_move` / `validate_director_decision`
8. **Memory layer (prompt read path)** — Episodic sections: `memory_layer/retrieval.py` and Host memory services
9. **Director** — Selection policy and prompts when evidence points here (Host prepare + DSH director phase + `prompt_builders.py`)
10. **Narrator** — Prose polish; dialogue must stay verbatim (DSH `narrator-phase.mjs`, `prompt_builders.py`)

---

## Simulation failure triage (layer-aware)

Use this when a supervised run or application session “looks wrong” and you are deciding which subsystem owns the fix. Scenario validation: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md); audit layout: [docs/audit-workflows.md](./docs/audit-workflows.md).

Apparent **UI vs API/runtime** differences are often **input-driven** (setup payload, opener, settings), not a second core. Align runs on scenario / opener inputs, retrieval settings, and inference mode before assigning a **Layer** defect. UI opener picks live in `v2/ui/streamlit_app.py` and are applied through the Node application API → Domain Host `session_setup`; tests and DSH suites supply the same setup through Host APIs.

### Workflow

1. Reproduce with audit/trace enabled. Note scenario id, baseline vs treatment, and whether the run used live or mock inference.
2. Pick **one primary Layer** first (canonical list below; full definitions in [governance/sources/issue-tracking-workflow.md](./governance/sources/issue-tracking-workflow.md) **§F**).
3. Walk **evidence order** once, top to bottom; stop when you can name what **committed** the bad state.
4. Produce **Layer**, **verdict**, and **minimal repro** (scenario id, audit/trace locator, turn index if known).
5. **Stop** — validation and triage end here. Do not implement fixes in the same pass unless a human **explicitly** directs remediation.

### Validation vs Remediation Boundary

- The validation path **observes, classifies, and reports**; it **stops** at **classification + minimal repro**.
- **No automatic remediation.** All fixes require **explicit human approval** and are implemented in a separate remediation phase.
- Do not rerun with altered conditions unless **explicitly instructed**.
- Invalid-run retries: [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md) → **Validation retry policy (invalid runs)**.

### Evidence order (strict)

1. **Structured move** — `action`, `dialogue`, `motivation`, `presence_changes`, raw character JSON.
2. **Consequences / classification** — Tags from `continuity_consequence_classifier.py`. Empty classifier lists do **not** imply no structural change; check committed events, issue updates, and allowlisted `scene_state_updates`.
3. **Continuity snapshot** — After the suspect turn: presence, issues/events (`ContinuityManager` / `SceneState`; Host session JSON).
4. **Selector / Director** — Eligibility, participation, Director decision (Host APIs + DSH director phase + round orchestrator).
5. **Narrator / rendered presentation last** — Confirms presentation; **do not** treat as proof of what continuity believed.

### Primary Layer (pick one to start)

Use [MODULE_INDEX.md](./MODULE_INDEX.md) for file-level routing. **Orchestration vs response_validation:** wrong **who acts next** → **`orchestration`**; wrong **validity of a produced move** → **`response_validation`**.

| Layer | Typical symptoms | First code to inspect |
|-------|------------------|------------------------|
| `consequence_classification` | Consequence list contradicts the structured move | `continuity_consequence_classifier.py`, `scene_exit_detection.py` |
| `continuity_state` | Wrong issues/events/scene fields **after** a turn | `continuity_manager.py`, `continuity_*` helpers; Host `kernel.py` `commit_move` |
| `progression` | Retry / gate / Q1–Q4 delta behavior | Continuity `turn_metadata` / Host commit path; domain progression helpers if present in-tree |
| `orchestration` | Wrong next actor, pool, address, continuation | `participation_policy.py`, DSH `director-phase.mjs`, `hg-round-orchestrator/service.mjs`, `response_validation_selection.py` |
| `response_validation` | Invalid/rejected character or narrator **payload** | `response_validation_parsing.py`, `response_validation_content.py` (`validate_bot_response_for_runtime`), `response_validation_presence.py`; Host `validate_move` |
| `grounding` | SETTLED SCENE FACTS / BINDING CONSTRAINTS wrong vs continuity | `scene_grounding.py`, `continuity_context_projector.py`, `prompt_builders.py` |
| `perception` | Wrong knowledge boundary in prompts | `perception_audibility.py`, Host projector, `prompt_builders.py` |
| `memory` | Episodic or retrieved bundle wrong given continuity | `memory_layer/`, Host `memory_service.py` / `retrieval_selection.py` |
| `rendering` | Prose garble, dialogue not verbatim in presented output | DSH `narrator-phase.mjs`, `prompt_builders.py` |
| `audit_simulation` | Wrong or missing traces, harness, metrics | DSH `hg-trace-emitter`; Host `session_history.py`; `v2/rp_runtime/tests/`; [docs/audit-workflows.md](./docs/audit-workflows.md) |
| `application_infrastructure` | Encoding, UI shell, session I/O, loader/path mechanics | `v2/ui/streamlit_app.py`, Host `session_repository.py` / `session_setup.py`, `session_manager.py`, env/paths |
| `other` | Only per **§F** | [governance/sources/issue-tracking-workflow.md](./governance/sources/issue-tracking-workflow.md) **§F** |

### Verdict (record one)

- **legitimate** — State change matches the structured move and rules.
- **legitimate but undesirable** — Rules behaved as implemented; outcome is a design or scenario weakness (**Type** `quality` or `design_gap`).
- **bug** — Implementation contradicts PRD/architecture; fix belongs in the **primary Layer**.
- **ambiguous** — Not enough evidence; isolate turn before coding.

### Success criteria

- There is a **default path** from “the run looked wrong” to **Layer-labeled** investigation **before** any **approved** code change.
- Repros stay **small** (scenario + session/trace locator).
- **Triage output is complete** when **Layer**, **verdict**, and **minimal repro** are recorded and the validation pass **stops**.

---

## By problem type

### Turn selection issues

- **Who speaks next** — `participation_policy.py`, DSH `director-phase.mjs`, `hg-round-orchestrator/service.mjs`, `response_validation_selection.py`.
- **Director ignores context** — Check the Host **prepared manifest** (`continuity_context_projector.py`, `kernel.prepare_director_context`), not only Director system text.

### Character drift (voice, tone, anchors)

- **Post-move checks** — `response_validation_content.py` (`validate_bot_response_for_runtime` for objective gates); semantic prose quality deferred to #19
- **Anchor source** — `character_state_model.py`, JSON cards under `data/characters/`
- **Semantic prose false positives** — bounded Character semantic evaluation (#19), not runtime regex heuristics in `validate_move`

### Presence bugs (`must_remain`, exits, absence)

- **Deterministic rules** — `response_validation_presence.py`, `scene_exit_detection.py`, `scene_template.py` / `scene_template_cohesion.py`
- **Selection vs presence** — If the actor should not have been eligible, inspect Host eligibility / DSH director phase after the deterministic validator.

### Duplicate dialogue / repeated outputs (R11 repetition/stagnation)

- **Production authority** — bounded Character semantic evaluation (#19): `character-semantic-evaluation.mjs`, DSH `character-phase.mjs` (soft finding, max one challenge; residual soft does not block)
- **Not a deterministic hard gate** — `response_validation_content.py` / `validate_bot_response_for_runtime` enforces objective contracts only (#18)
- **Retry behavior** — DSH character phase attempt loop (unified candidate budget) + Host `validate_move` for objective failures
- **Evidence** — execution evidence semantic index; `tools/investigation/list_execution_evidence.py --dimension R11`

### Knowledge leaks / wrong “who knows what”

- **Prompt assembly first** — `perception_audibility.py`, Host projector, `prompt_builders.py`
- **Continuity propagation** — `continuity_knowledge_helpers.py`, `continuity_manager.py`

### Persistence / reload issues

- **Session / continuity blobs** — Host `session_repository.py`, domain `session_manager.py`
- **Scene state fields** — `SceneState` and `ContinuityManager.to_dict()` / `.from_dict()` before blaming prompt assembly
- **UI cache** — `v2/ui/streamlit_app.py` only stores presentation fields; it is not the persistence authority

### Scene start / first-round user line

- **Canonical setup** — Host `session_setup.py`, `continuity_setup_seam_v77.py`, `opening_prompt.py`; DSH `opening-phase.mjs`
- **UI opener pick** — `v2/ui/streamlit_app.py` → Node application API → Host setup
- **Scenario contract** — `progression_simulation_scenarios.py`; [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md)

### Settled sleeping assignment / housing-call re-litigation

- **Continuity-owned resolved outcome first** — `resolved_outcome_registry.py`, `resolved_outcome_engine.py`, `continuity_resolved_outcomes.py`, `continuity_manager.py`
- **Grounding projection second** — `scene_grounding.py` into Host character/director context

### Audit output / regression analysis

- **Layout and file meanings** — [docs/audit-workflows.md](./docs/audit-workflows.md)
- **Writers / traces** — DSH `hg-trace-emitter`; Host `session_history.py`
- **Committed truth** — `ContinuityManager` / session JSON, not presentation text alone

---

## Layer responsibility (who owns what)

| Layer | Owns |
|-------|------|
| **Ingestion** (future) | Source extraction, graph/vector stores — not live turn loop |
| **Packaging** | Bounded turn context / packets — not replacing continuity truth. Production assembly is Domain Host projection + `prompt_builders.py` |
| **Domain library** (`v2/domain/modules/`) | Continuity, validation rules, prompt text, perception, grounding, templates, `SessionManager` format |
| **Domain Host** (`v2/domain_api/`) | Authoritative session/round APIs, context construction, validate, commit |
| **DSH runtime** (`v2/rp_runtime/`) | Round sequencing, inference, provider execution, context transport |
| **UI** (`v2/ui/`) | Presentation only |

---

## Related

- [GLOSSARY.md](./GLOSSARY.md)
- [PACKET_CONTRACTS.md](./PACKET_CONTRACTS.md) — future seam; do not implement retrieval as authoritative state
- [SCENARIO_VALIDATION_FRAMEWORK.md](./SCENARIO_VALIDATION_FRAMEWORK.md)
- [docs/audit-workflows.md](./docs/audit-workflows.md)
