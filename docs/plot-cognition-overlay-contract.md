# Plot Cognition Overlay contract

**Status:** Normative semantic contract — Issue **#58** Phase 1 (`consensus_reached`)  
**Executable binding:** `v2/domain_api/plot_cognition_overlay_contract.py`  
**Parent program:** Issue **#48** — Storyteller persistent narrative cognition  
**Architecture anchor:** `4f917d7982226b935a522a96efae03da040fc87c`

This document is the **authoritative human-readable specification** for Storyteller Plot Cognition Overlay semantics. If this document and the Python binding diverge, resolve through governed Issue amendment and restore parity via contract tests.

**Not in scope here:** persistence (#59), initialization (#60), update/replan (#61), consumer projection (#62), orchestration (#63), forensic evidence implementation (#64), scenario validation (#65).

---

## Purpose

Holy Grail Storyteller currently performs **round-local Model A** advisory cognition (`StorytellerAdvisoryPackage`), invalidated on authoritative commit. The Plot Cognition Overlay is a **bounded, persistent, cross-commit** representation of Storyteller's evolving **advisory** understanding of where the RP could productively go.

Authority flow:

```text
Storyteller proposes (overlay + Model A)
        ↓
downstream roles decide / enact / modify / ignore
        ↓
Continuity establishes authoritative reality
        ↓
Storyteller adapts plot cognition (overlay)
```

---

## Authority boundary

| Concern | Owner |
|---------|--------|
| Authoritative world truth | **Continuity** |
| Advisory plot cognition | **Storyteller overlay** (this contract) |
| Round-local assessment package | **Model A** (`storyteller_contract.py`) |
| Turn selection / enactment | **Director** / **Character** |
| Forensic change history | Evidence plane (**#64**) — obligations defined here, implementation deferred |

Overlay cognition is **non-authoritative**. `basis_refs` and `continuity_issue_refs` are **pointers** to authority, not copies of authoritative state. No overlay field may write or imply Continuity truth.

---

## Overlay categories

Exactly three persistent cognition categories:

1. **PlotGoal** — intended direction Storyteller may pursue or nudge toward
2. **UnresolvedNarrativePressure** — observation/interpretation of unresolved dramatic potential
3. **GlobalPlotFrame** — small ensemble-level meta-context (not a second goal system)

The overlay is:

- persistent across commits **conceptually** (persistence mechanics → #59)
- bounded **conceptually** (numeric policy → #59)
- **operative advisory cognition** for Storyteller reasoning
- separate from transient Model A
- separate from durable forensic history

---

## Model A boundary

| Aspect | Model A | Plot Cognition Overlay |
|--------|---------|------------------------|
| Lifetime | Round-local; invalidated on authoritative commit | Cross-commit; adapts rather than wholesale invalidation |
| Primary type | `StorytellerAdvisoryPackage` | `PlotGoal`, `UnresolvedNarrativePressure`, `GlobalPlotFrame` |
| Consumption | Projected to Director/Character/Narrator lanes | May **inform** Model A orientation/assessment (#60+) |
| Degradation | Existing Model A degradation when unavailable | Model A may run with empty overlay input |

Schemas and lifetimes **must not** be merged. This Issue does not modify Model A behavior.

---

## Grounding decomposition

Grounding classifies the **basis**, not the whole cognition object.

| Field | Applies to | Meaning |
|-------|------------|---------|
| `basis_note` | Goals, pressures, frame (optional) | Semantic description of established/inferred context motivating cognition |
| `basis_refs` | Goals, pressures, frame | Stable references to evidence/authority — **not copies** |
| `intended_direction` | **PlotGoal only** | Advisory pursuit intent; always non-authoritative |

Permitted combinations:

- Strong authoritative basis + prospective direction
- Inferred basis + prospective direction
- Storyteller-originated direction without stable authoritative refs

**Excluded:** whole-object `grounding_kind`; `mixed` grounding enum.

---

## PlotGoal

```text
PlotGoal
├── goal_id
├── intended_direction                 # REQUIRED; non-empty; always advisory
├── basis_note
├── basis_refs
├── applicability
├── planning_horizon: LONG | MEDIUM | SHORT
├── creation_provenance
├── lineage (parent_goal_id, superseded_by_goal_id)
├── activity_state: active | inactive | retired
├── momentum_note
└── feasibility_note
```

### Field semantics

- **`intended_direction`** — where Storyteller thinks the story could productively go; never authoritative fact.
- **`basis_*`** — committed/inferred reality motivating the goal; may be empty for wholly Storyteller-invented direction.
- **`planning_horizon`** — semantic scope (LONG/MEDIUM/SHORT); not a slot. Multiple goals may share horizon and Character.
- **`momentum_note` / `feasibility_note`** — optional semantic movement/constraint notes; not lifecycle enums.
- **`lineage`** — spawn/supersession references; forensic detail deferred to #64.

**Excluded:** `rank_hint`, numeric caps, whole-goal grounding enums.

---

## UnresolvedNarrativePressure

```text
UnresolvedNarrativePressure
├── pressure_id
├── pressure_text                      # REQUIRED
├── dramatic_rationale                 # REQUIRED
├── basis_note
├── basis_refs
├── continuity_issue_refs              # reference only
├── applicability
├── creation_provenance
├── activity_state
└── related_goal_ids                   # optional
```

### Semantic distinction (primary classifier)

| Kind | Definition |
|------|------------|
| **Continuity issue** | Authoritative blocked/unresolved **world state** |
| **Pressure** | Storyteller **observation** of unresolved dramatic potential |
| **PlotGoal** | Storyteller **intended pursuit** direction |

`basis_refs` presence or absence is **not** a structural classifier. Pressures may have authoritative refs, issue refs, inferred basis via `basis_note`, or no convenient stable ref when semantic basis is still understandable.

Pure Storyteller invention proposing a new direction/entity is ordinarily a **PlotGoal** because it expresses intended pursuit — not because refs are empty.

Objective validators enforce **structure only**, not prose semantics.

---

## GlobalPlotFrame

```text
GlobalPlotFrame
├── frame_id
├── direction_sense                    # REQUIRED
├── pacing_note
├── cross_character_note
├── opportunity_note
├── basis_refs
├── activity_state: active | inactive
├── superseded_by_frame_id
└── creation_provenance
```

- Structured notes enable partial update/replan (#61) and field-level forensic diff (#64) without re-parsing a monolithic blob.
- **No** numeric character/token limits in Phase 1.
- **No** goal collection inside the frame. Global goals use `PlotGoal` with `applicability_kind=global`.
- Consumed primarily during Model A synthesis; raw Character projection deferred to #62.

---

## Applicability

```text
CognitionApplicability
├── applicability_kind: character | relational | global
├── primary_character_id
└── involved_character_ids
```

### Validation rules

| Kind | Rules |
|------|-------|
| **character** | Exactly one involved Character; `primary_character_id` required and equal to that Character |
| **relational** | Two or more involved Characters; `primary_character_id` required and must be among involved |
| **global** | `involved_character_ids` empty; `primary_character_id` null |

This is **not** a relationship graph. Relational applicability supports multi-character cognition without misclassifying it as global.

---

## Creation provenance

Immutable **semantically** after cognition creation.

```text
CreationProvenance
├── source: authored_material | storyteller | character_committed | player_committed
├── provenance_note
└── provenance_refs
```

- Record a **primary source** where genuinely clear.
- `provenance_note` and `provenance_refs` may preserve **multiple material contributors** when a committed development reflects more than one origin.
- Do **not** force lossy single-origin interpretation.

**Not creation sources:** `adaptation`, `update`, `replan`, `supersede` — those are change-lineage semantics (#64).

---

## Lifecycle (`activity_state`)

| State | Meaning |
|-------|---------|
| `active` | In bounded operative set; eligible for Storyteller/Model A consumption |
| `inactive` | Dormant/deprioritized; retained in overlay but excluded from operative consumption |
| `retired` | Cognitively abandoned/superseded/outgrown; eligible for evidence-only retention |

`GlobalPlotFrame` uses `active | inactive` only (no `retired` on frame contract).

**Transition reasons** belong in forensic evidence (#64), not in the lifecycle enum.

---

## Boundedness (Phase 1 invariant only)

> The operative Plot Cognition Overlay is finite and policy-bounded by category/scope.

Deferred to **#59:** numeric caps, persisted rank, eviction algorithms, replenishment algorithms, persistence policies.

Any prioritization, inactivity, retirement, or eviction that materially changes active cognition must be **forensically reconstructable** (#64 obligation).

---

## Forensic obligation profile (#58 normative; #64 implementation)

Later evidence MUST allow reconstruction of:

```text
prior cognition
→ relevant trigger/input
→ semantic determination
→ resulting cognition
→ projection or non-projection
→ enactment/modification/ignoring
→ authoritative outcome
→ later Storyteller adaptation
```

Requirements:

- Material changes require **semantic text/context**; IDs/enums/hashes alone are insufficient.
- Creation provenance must remain reconstructable.
- Active overlay is **not** append-only history.

**#64 owns:** event classes, serialization, persistence layout, indexing, query tooling, retention.

---

## Downstream ownership

| Issue | Responsibility |
|-------|----------------|
| **#59** | Persistence, lifecycle policy, boundedness caps/eviction |
| **#60** | Plot cognition initialization |
| **#61** | Update, semantic replan, frame evolution |
| **#62** | Consumer projection, epistemic isolation |
| **#63** | Orchestration, integration |
| **#64** | Forensic evidence plane, cross-seam lineage |
| **#65** | Scenario-grade program validation |

---

## Schema identifiers

| Type | Schema constant |
|------|-----------------|
| PlotGoal | `hg_plot_goal_v1` |
| UnresolvedNarrativePressure | `hg_unresolved_narrative_pressure_v1` |
| GlobalPlotFrame | `hg_global_plot_frame_v1` |

---

## Executable binding

Structural validation, serialization, and round-trip helpers live in:

`v2/domain_api/plot_cognition_overlay_contract.py`

Contract parity tests: `v2/domain/tests/test_plot_cognition_overlay_contract.py`
