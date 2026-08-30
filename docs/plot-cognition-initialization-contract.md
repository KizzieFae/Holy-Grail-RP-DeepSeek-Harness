# Plot Cognition initialization contract

**Status:** Normative initialization contract — Issue **#60**  
**Semantic contract:** [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md) (#58)  
**Persistence contract:** [plot-cognition-overlay-persistence-contract.md](./plot-cognition-overlay-persistence-contract.md) (#59)  
**Executable binding:** `v2/domain_api/plot_cognition_initialization_*.py`  
**Parent program:** Issue **#48**

Defines how Storyteller constructs **initial** Plot Cognition Overlay current state from bounded authored/setup inputs. Does not define ongoing update/replan (#61), projection (#62), orchestration (#63), durable forensic storage (#64), or scenario tuning (#65).

---

## Purpose

When a `plot_cognition_scope_id` has no initialized overlay (`ABSENT`), the system may run a **one-time initialization** that semantically adopts advisory cognition from available source material and persists a valid #59 current snapshot.

Initialization is an **explicit domain capability**. It is **not** Model A behavior.

---

## Core model

```text
authoritative/authored source material
        ↓
InitializationSourceSnapshot (+ fingerprint)
        ↓
Storyteller semantic adoption inference (#63)
        ↓
PlotCognitionInitializationProposal
        ↓
objective validation (deterministic)
        ↓
semantic evaluation contract (#63 invokes evaluator)
        ↓
materialize #58 cognition
        ↓
freshness recheck + ABSENT + CAS
        ↓
persist through #59 → READY
```

No source item becomes overlay cognition without Storyteller semantic adoption.

---

## Character motivation vs Storyteller intention

```text
Character motivation ≠ Storyteller intention
```

Character card goals, motivations, relationships, and circumstances are **semantic inputs only**. Initialization may adopt:

- `PlotGoal`
- `UnresolvedNarrativePressure`
- `GlobalPlotFrame` contribution
- **nothing**

There is **no** deterministic `card goal → PlotGoal` mapping.

---

## Basis, provenance, and intended direction

| Field | Role |
|-------|------|
| `basis_note` / `basis_refs` | Established/inferred context motivating cognition |
| `intended_direction` | Storyteller advisory pursuit (goals only) |
| `creation_provenance` | Origin of the **cognition object** |

Normal initialization-generated cognition uses `creation_provenance.source = storyteller`. Authored contributors are preserved via `basis_refs` and `provenance_refs` / `provenance_note`.

**Narrow exception:** `authored_material` creation provenance is permitted only when the cognition object is explicitly authored Storyteller-facing plot direction, evidenced by a `storyteller_plot_direction` provenance ref. Character motivations and scenario facts alone do **not** qualify.

---

## Opening readiness

Initialization occurs only after all opening presentation intended to precede play is durable.

| Mode | Opening completeness | Init may run |
|------|---------------------|--------------|
| `minimal` | `prose_not_expected` | After session baseline |
| `custom` / `template` | `prose_present` when `rp_history` opening exists | After session create (when prose present) |
| `generated` | `prose_pending` until `persist_opening_presentation`; then `prose_present` | After opening persist |

`InitializationSourceSnapshot.opening_completeness` exposes this structurally for #63.

---

## Zero cognition validity

Successful initialization is a persisted `READY` snapshot (`store_revision ≥ 1`), not a minimum cognition count.

Valid examples:

```text
goals={}, pressures={}, active_frame=null
goals={}, pressures={...}, active_frame=optional
```

---

## Source snapshot and fingerprint

`InitializationSourceSnapshot` captures semantically relevant inputs using stable refs and content digests — not full authoritative copies.

`fingerprint` is a deterministic SHA-256 of the canonical snapshot body. Ephemeral `snapshot_id` does not affect fingerprint equality.

Filesystem mtimes, wall-clock timestamps, and random IDs are **not** freshness authorities.

---

## Proposal and evaluation contracts

- `PlotCognitionInitializationProposal` (`hg_plot_cognition_init_proposal_v1`)
- `PlotCognitionInitializationEvaluation` (`hg_plot_cognition_init_eval_v1`)

#60 defines schemas and **objective** validators only. Semantic judgment (railroading, goal vs pressure quality, cast relevance) is **evaluator responsibility** (#63). No regex/keyword narrative evaluators in domain code.

Bounded correction pattern (orchestrated by #63):

```text
generator → deterministic metadata enrichment (#68 Part C)
→ objective validation → semantic evaluator
→ accept OR one revision → enrichment → objective validation → accept/fail
```

**Inference vs persistence (#68 Part C):** Model-facing init proposals supply semantic cognition fields only. Domain enrichment stamps missing deterministic metadata (`schema`, Storyteller `creation_provenance`, initial `activity_state`) immediately before objective validation. The persisted overlay DTO is not identical to the raw inference schema.

No separate curator role. Over-budget proposals return `budget_exceeded`; semantic revision must reduce/merge — no deterministic truncation.

---

## Idempotency

| Store status | Initialization |
|--------------|----------------|
| `ABSENT` | Eligible (if sources ready) |
| `READY` (including empty) | Never re-initialize |
| `CORRUPT` / `UNSUPPORTED_VERSION` / `DEGRADED` | Blocked |

---

## Concurrency

Do **not** hold plot-cognition scope lock across model inference.

Persist path (under #59 lock): re-load, verify fingerprint, verify `ABSENT`, CAS `expected_revision`, persist.

---

## Assimilation anchor

V1 initialization before first domain commit sets:

```text
assimilated_through_domain_commit_id = null
```

Opening presentation persistence does not fabricate domain commit ancestry.

---

## Forensic handoff (#64 deferred)

`InitializationForensicHandoff` carries ephemeral semantic evidence (source snapshot, proposals, evaluations, accepted cognition, commit result). #60 does **not** implement durable history. No `synthesis_kind` parallel taxonomy.

---

## Librarian / Retrieval

V1 initialization does not consume Librarian or Retrieval. Current authored/setup/Continuity inputs are sufficient; no demonstrated requirement justifies that dependency today. This is **not** an eternal prohibition.

---

## Ownership

| #60 | #63 |
|-----|-----|
| Source snapshot, fingerprint, contracts, objective validation, materialization, commit precondition | Trigger timing, model calls, retry orchestration, degradation |

---

## Downstream

| Issue | Responsibility |
|-------|----------------|
| **#61** | Update/replan after commits |
| **#62** | Consumer projection / epistemic isolation |
| **#63** | Runtime orchestration and model invocation |
| **#64** | Durable forensic evidence |
| **#65** | Scenario validation / policy tuning |
