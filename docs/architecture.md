# Architecture guidance

Shared guardrails for Holy Grail RP. Product orientation: [governance/sources/architecture-overview.md](../governance/sources/architecture-overview.md). File routing: [MODULE_INDEX.md](../MODULE_INDEX.md).

**Authored JSON boundaries:** [AUTHORED_SOURCE_CONTRACT.md](../AUTHORED_SOURCE_CONTRACT.md).

**Scenario validation:** [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md) (canonical; do not duplicate here).

**Issue workflow:** [governance/sources/issue-tracking-workflow.md](../governance/sources/issue-tracking-workflow.md).

---

## Repository stance

- Preserve module boundaries unless the task requires a boundary change.
- Prefer incremental fixes at the correct layer over architectural expansion.
- Avoid parallel implementations when an existing path can be corrected.
- Keep compatibility facades stable unless callers are explicitly in scope.

---

## Runtime stack

```text
Presentation (v2/ui/streamlit_app.py)
        ↓ HTTP
Node application / DSH runtime (v2/rp_runtime/)
        ↓ HTTP (domain-api-client)
Domain Host (v2/domain_api/)
        ↓
domain library (v2/domain/modules/)
        ↓
data/  (HG_DATA_DIR)
```

**Domain truth** lives in continuity and Host repositories. **Speaker selection** is Host participation policy plus DSH Director phase. **Inference** runs through DSH. **Context construction** is Domain Host **`PromptContributionManifest`** projection (`kernel.prepare_context`, including **`recent_scene_transcript`** / **`user_turn_trigger`** from `rp_history`; Director/Narrator additionally receive bounded **`scene_setup`**, live **`scene_state`**, and authoritative **`scene_progression`** from committed continuity); `HgContextBridge` only transports manifests. Domain `prompt_builders.py` retains legacy formatting helpers but is not the live V2 composition path. Packaging does not replace continuity authority. Node calls the Domain Host; Python does not call DSH.

---

## Behavioral validation layer

Scenario validation is a **core architectural layer**: fixed JSON scenarios, domain manifest tests, integration tests, optional audit JSON, and offline investigation tools.

Canonical spec: [SCENARIO_VALIDATION_FRAMEWORK.md](../SCENARIO_VALIDATION_FRAMEWORK.md).

---

## Domain architecture rules

Holy Grail RP uses Director + character agents + Narrator + continuity manager.

### Scene-start spine

Fresh scenes use one canonical continuity init/apply ordering (`continuity_setup_seam_v77`, Host `session_setup.py`). Application UI and test/runtime inputs are **separate surfaces** into that spine—not divergent template-application models.

**Opener selection (UI):** template-owned Opener JSON or custom text; multiple template openers require an explicit pick before scene start. The UI posts that choice through the Node application API. Test and DSH paths carry opener choice on Host session-create payloads. DSH `opening-phase.mjs` runs opening inference when the setup requests generated opening text.

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
- Keep the Domain Host as the composition boundary; keep the UI a presentation client.
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
8. Director logic (Host prepare/validate + DSH director phase)
9. Narrator rendering polish (DSH narrator phase)

Full workflow: [audit-workflows.md](./audit-workflows.md).

---

## Validation modules

Runtime validation is split under `v2/domain/modules/`:

- `response_validation.py` — facade
- `response_validation_parsing.py` — JSON / move parsing
- `response_validation_content.py` — **production runtime** (`validate_bot_response_for_runtime`: objective R02a placeholders + R03 move-shape/registry); **offline scenario** (`validate_bot_response_for_scenario` for investigation recall)
- `response_validation_presence.py` — `must_remain` helpers (`get_must_remain_characters`)
- `response_validation_selection.py` — eligibility helpers (non-authoritative vs Host/DSH Director selection)

Host `validate_move` calls `validate_bot_response_for_runtime` only. Deterministic textual/semantic quality heuristics (R02b, R11–R15) are **not** objective hard gates in Domain validation.

**Bounded Character semantic evaluation (#19):** DSH Character orchestration runs `generate → objective validate → bounded semantic evaluate → commit`. Semantic judgment lives in DSH (`character-semantic-evaluation.mjs`), not `kernel.validate_move`. The Host exposes read-only evaluation context via `prepare_semantic_evaluation_context` and delivers orchestration-only correction via `semantic_correction` manifest contributions on `prepare_context`. The evaluator does not mutate continuity, write RP, or enter canonical history. Hard findings require a valid authority reference from the evaluation context; soft findings allow one challenge then residual recording. Maximum three generated Character candidates per turn (`min(configured limit, 3)`). Full forensic chains are preserved in execution evidence (#15).

Validators **reject or annotate**; they do not replace Director selection or continuity commits.

**Director fallback:** on JSON parse failure, Host/DSH decision handling may record `"source": "fallback"`. Turn-selection preemption validation is skipped for fallback decisions; memory writes for committed turns are not.

---

## Memory layer

**Policy owner** for episodic writes and prompt read/format. `CharacterState` holds storage plus identity/relationship prompt text.

- **Writes:** commit-time only, perception-filtered observers (`memory_layer/facade`, `writes`, `storage`).
- **Reads:** `memory_layer/retrieval.py` builds episodic sections for `state_context`.

### Prompt context contract

- Character/Director/Narrator **interpretation** is composed in Domain Host (`continuity_context_projector.py`, `kernel.prepare_*`) using domain `prompt_builders.py` and memory/retrieval services.
- `prompt_builders` formats prompt text; it does not re-read memory buckets or own round sequencing.
- DSH `HgContextBridge` registers the Host manifest on an ephemeral inference agent and does not reinterpret authority classes.

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
