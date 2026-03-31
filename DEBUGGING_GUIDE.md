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
3. **Scene grounding** — Does `scene_grounding` reflect continuity (settled facts present, not stale, not empty when extraction promoted)? (`scene_grounding.py`, `prompt_builders.py` formatting only after 1–2 look sane for that symptom)
4. **Orchestration state** — Spotlight, forced speaker, continuation override (`orchestration_helpers.py`, `st.session_state` keys used in `app_turn_director.py`)
5. **Summaries / retrieval windows** — What the prompt actually sees (`summary_audit_helpers.py`, `prompt_builders.py` only after earlier layers look sane)
6. **Validation boundaries** — Parsing, presence, drift, selection (`response_validation_*.py`)
7. **Director** — Selection policy and prompts when evidence points here
8. **Narrator** — Prose polish; dialogue must stay verbatim (`app_turn_rendering.py`)

---

## By problem type

### Turn selection issues

- **Who speaks next** — `orchestration_helpers.py` (address / continuation / caps), `app_turn_director.py` (Director call and overrides), `response_validation_selection.py`, then `semantic_validation.py` for reconciliation.
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

### Settled sleeping assignment re-litigation

- **Continuity-owned resolved outcome first** — inspect `resolved_outcome_registry.py`, `resolved_outcome_engine.py`, `continuity_resolved_outcomes.py`, `continuity_manager.py`, and `turn_metadata_by_index[*]["resolved_outcomes"]["sleeping_surface"]` before editing prompt wording. Identical-value reassertion surfaces as `no_op_existing_value`.
- **Grounding projection second** — confirm `scene_grounding.py` reflects the active `assignment:sleeping_surface` outcome into SETTLED SCENE FACTS.
- **Template slots / move field** — verify the scene exposes bounded `sleeping_surface_slots` and the structured move includes `scene_state_updates.sleeping_surface_assignment` only when the beat truly settles the assignment.

### Settled housing-call re-litigation

- **Continuity-owned resolved outcome first** — inspect `resolved_outcome_registry.py`, `resolved_outcome_engine.py`, `continuity_resolved_outcomes.py`, `continuity_manager.py`, and `turn_metadata_by_index[*]["resolved_outcomes"]["housing_call"]` before editing prompt wording. Identical-value repetition surfaces as `no_op_existing_value`.
- **Grounding projection second** — confirm `scene_grounding.py` reflects the active `communication_state:housing_call` outcome into SETTLED SCENE FACTS.
- **Move field discipline** — verify structured output uses only `scene_state_updates.housing_call_outcome` with terminal `status` values `completed` or `failed`, never planning or in-progress chatter.
- **No lexical emission** — `compute_grounding_markers` does **not** add `communication_state:housing_call` on new turns; older sessions may still carry that marker on saved `PublicEvent` rows, which rebuild can read without conflicting with an active resolved outcome for the same slot.

### Audit output / regression analysis

- **Layout and file meanings** — `autogen_rp/python/rp_app/AUDIT_DOCUMENTATION.md`
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
