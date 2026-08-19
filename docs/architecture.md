# Architecture guidance

Shared guardrails for Holy Grail RP. Product orientation: [ARCHITECTURE_OVERVIEW.md](../ARCHITECTURE_OVERVIEW.md). File routing: [MODULE_INDEX.md](../MODULE_INDEX.md).

**Authored JSON boundaries:** [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md).

**Scenario validation:** [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md) (canonical; do not duplicate here).

**Issue workflow:** [governance/rp-app/issue-tracking-workflow.md](../governance/rp-app/issue-tracking-workflow.md).

---

## Repository stance

- Preserve module boundaries unless the task requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless callers are explicitly in scope.

---

## Runtime stack

```text
Application client / UI
        ↓
Domain API client
        ↓
RP runtime (DSH / Cordis)  ↔  Domain Host (v2/domain_api)
        ↓
domain library (v2/domain/modules/)
        ↓
data/  (HG_DATA_DIR)
```

**Domain truth** lives in continuity and repositories. **Orchestration** selects speakers and merges structured history. **Inference** runs through DSH. **Packaging** assembles bounded prompt context; it does not replace continuity authority.

---

## Behavioral validation layer

Scenario validation is a **core architectural layer**: fixed JSON scenarios, domain manifest tests, integration tests, optional audit JSON, and offline investigation tools.

Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Domain architecture rules

Holy Grail RP uses Director + character agents + Narrator + continuity manager.

### Scene-start spine

Fresh scenes use one canonical continuity init/apply ordering (`scene_start_bootstrap`, `restore_or_initialize_continuity_manager`). Application UI and harness inputs are **separate surfaces** into that spine—not divergent template-application models.

**Opener selection (UI):** template-owned Opener JSON or custom text; multiple template openers require an explicit pick before scene start. Harness paths carry opener choice via scenario/bootstrap composition.

### Core responsibilities

- Character agents produce self-only structured moves.
- Optional move fields are **not** the authority boundary for issues, tension, or consequences.
- Director selects who acts next.
- Narrator renders prose and preserves character dialogue verbatim.
- Continuity manager updates durable scene and issue state.
- Validation and enforcement remain separate from prompt styling.
- **`perception_audibility.py`** gates who may see dialogue and narrator render for others' beats.

### Protected intent

- Do not move long-horizon continuity into prompts or unbounded transcripts.
- Do not treat Director prompt edits as the default runtime fix.
- Keep application composition layers thin.
- **Progression advisory** is advisory only — it must not write continuity truth or mutate `CharacterState`.
- **Scene Grounding** is read-only prompt projection from continuity — not a second authority ([PRD](../Holy%20Grail%20PRD.md) §5.8, [scene-grounding-layer.md](./scene-grounding-layer.md)).

---

## Change strategy

1. Identify the real layer involved.
2. Inspect downstream consumers.
3. Prefer the smallest fix that preserves the design.
4. Update shared docs when contracts change.

---

## RP audit diagnosis order

When debugging scene quality or continuity:

1. continuity and state representation
2. perception / audibility (knowledge leaks, whispers, per-character prompt mismatch)
3. scene grounding (settled facts present, stale, or missing)
4. issue lifecycle and orchestration state
5. summary retrieval and compression
6. validation and enforcement boundaries
7. memory layer read path (`memory_layer/retrieval.py`)
8. Director logic
9. Narrator rendering polish

Full workflow: [audit-workflows.md](./audit-workflows.md).

---

## Validation modules

Runtime validation is split under `v2/domain/modules/`:

- `response_validation.py` — facade
- `response_validation_parsing.py` — JSON / move parsing
- `response_validation_content.py` — structural checks
- `response_validation_drift.py` — identity anchors
- `response_validation_presence.py` — presence / `must_remain`
- `response_validation_selection.py` — turn-selection checks (non-authoritative)

Validators **reject or annotate**; they do not replace Director selection or continuity commits.

**Director fallback:** on JSON parse failure, `decision` includes `"source": "fallback"`. Turn-selection preemption validation is skipped for fallback decisions; memory writes for committed turns are not.

---

## Memory layer

**Policy owner** for episodic writes and prompt read/format. `CharacterState` holds storage plus identity/relationship prompt text.

- **Writes:** commit-time only, perception-filtered observers (`memory_layer/facade`, `writes`, `storage`).
- **Reads:** `memory_layer/retrieval.py` builds episodic sections for `state_context`.

### `state_context` contract

- Composed only in `app_turn_prompting.build_character_turn_prompt` via `build_character_state_context_for_prompt`.
- `prompt_builders` inserts `state_context` unchanged — no direct re-read of memory buckets.

---

## Continuity authority and evidence lanes

**`SceneState`** and **`process_turn`** define committed truth. Distinguish **intent**, **interpretation**, **commit**, and **observation**. Narrator prose and classifier signals do not override `SceneState`.

Details: continuity modules under `v2/domain/modules/continuity_*.py`, [audit-workflows.md](./audit-workflows.md).

---

## Issue #240 / #249 character prompt topology

Default character prompt topology uses harmonized teaching blocks. Environment rollback flags exist for investigation fixtures; production defaults are defined in domain modules and tests under `v2/domain/tests/fixtures/issue240/` and `issue251/`.

---

## Related

- [rp-data-layout.md](./rp-data-layout.md) — on-disk data
- [scene-grounding-layer.md](./scene-grounding-layer.md) — Scene Grounding MVP
- [PACKET_CONTRACTS.md](../PACKET_CONTRACTS.md) — packet seam intent
