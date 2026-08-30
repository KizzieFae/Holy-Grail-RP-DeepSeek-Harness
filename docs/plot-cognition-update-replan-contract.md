# Plot Cognition update and semantic replan contract

**Status:** Normative update/replan contract — Issue **#61**  
**Semantic contract:** [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md) (#58)  
**Persistence contract:** [plot-cognition-overlay-persistence-contract.md](./plot-cognition-overlay-persistence-contract.md) (#59)  
**Initialization contract:** [plot-cognition-initialization-contract.md](./plot-cognition-initialization-contract.md) (#60)  
**Executable binding:** `v2/domain_api/plot_cognition_update_*.py`  
**Parent program:** Issue **#48**

Defines how Storyteller assimilates authoritative post-initialization reality into Plot Cognition Overlay current state, and how semantic replan differs from update. Does not define projection (#62), orchestration (#63), durable forensic storage (#64), or scenario tuning (#65).

---

## Fundamental split

```text
domain_commit_id           = committed-move lineage
continuity_version         = per-session persisted-state invalidation generation
authority_source_fingerprint = deterministic identity of Plot-Cognition-relevant authoritative material
```

`continuity_version` changing does **not** automatically require semantic inference. It triggers re-projection and fingerprint comparison.

---

## Objective authority unchanged vs semantic no-change

| Outcome | Trigger | Model call | Cognition change |
|---------|---------|------------|------------------|
| `objective_authority_unchanged` | cv changes, fingerprint identical | No | No |
| `semantic_no_change` | fingerprint changes, Storyteller determines no cognition change | Yes | No |
| `semantic_update` | fingerprint changes, update accepted | Yes | Yes |
| `semantic_replan` | update requests replan + replan accepted | Yes | Yes |

Never conflate objective authority unchanged with semantic no-change.

---

## Relevant-authority projection

`build_plot_cognition_authority_projection` produces a canonical semantic body including:

- Continuity scene state, issues, public events, scene grounding, character states
- Committed move lineage through applicable `through_domain_commit_id`
- Host-accepted #49 B2 `environmental_descriptor` derived story knowledge only

Digest fields (`summary_digest`, `move_digest`, etc.) establish deterministic identity for `authority_source_fingerprint`.

**Runtime semantic inference** additionally receives `semantic_authority_excerpts` on the update source snapshot: bounded verbatim text from existing authoritative Continuity/Domain state (`PublicEvent.summary`, issue descriptions, scene-grounding statements, committed-move excerpts when no public-event summary exists). This parallel transport is **not** included in the fingerprint; it supplies readable context for Storyteller update/replan reasoning without digest interpretation or Chronicle runtime reads.

**Prior operative cognition** (`prior_operative_cognition`, schema `hg_plot_cognition_prior_operative_cognition_v1`) is also supplied on the update source snapshot and production inference manifest. It is a bounded, active-only projection of the operative Plot Cognition overlay (active goals with `goal_id`, `intended_direction`, `planning_horizon`, `grounding`, and applicability scope; active pressures with `pressure_id` and `pressure_text`; operative global frame with `frame_id` and `ensemble_context` when present). It is **advisory comparison context only** — not authoritative evidence and **not** included in `authority_source_fingerprint`. Authoritative Continuity-derived excerpts remain authoritative over prior Storyteller cognition.

Excluded from authority projection: presentation-only history, skip/audit metadata, rejected B2, K2 occurrence duplicates of already-represented public events.

---

## Assimilated authority metadata (#59 successor extension)

```text
assimilated_authority:
  schema: hg_plot_cognition_assimilated_authority_v1
  sessions:
    - hg_scene_id
      through_domain_commit_id
      through_continuity_version
      authority_source_fingerprint
```

Legacy scalar `assimilated_through_domain_commit_id` remains for backward compatibility. It records committed-move lineage considered through that commit — **not** authoritative freshness proof. For sole contributors it stays synchronized with the vector entry.

Existing stores without `assimilated_authority` remain `READY` with **freshness unknown** (`freshness_unprovable`). They must not be treated as corrupt or re-initialized.

---

## Update vs replan

**Update** assimilates authoritative reality into existing cognition (retain, advance, ground, modify, inactivate, supersede, frame adjustment).

**Replan** changes what Storyteller wants the story to pursue. An update may set `replan_required`; replan is a separate proposal/evaluation stage.

At update inference time, the production prompt requires semantic comparison of new authoritative evidence against `prior_operative_cognition`:

| Judgment | Meaning | Typical signals |
|----------|---------|-----------------|
| `no_change` | Authoritative change does not materially require cognition alteration | `overall_result=no_change`, `replan_required=false` |
| Assimilable update | New authority changes relevant cognition but operative strategic direction remains viable | `replan_required=false`, incremental goal/pressure/frame adjustments |
| Invalidation replan | New authority materially invalidates assumptions, trajectories, targets, or strategic direction | `replan_required=true`, complete `replan_proposal` + `replan_evaluation`, `update_evaluation.overall_result=accept` when package is complete |

### `overall_result` vs strategic revision

`update_evaluation.overall_result` disposes the **generated package** toward commit, not whether the old strategy should change:

| Value | Meaning |
|-------|---------|
| `accept` | Generated update package is commit-ready. May coexist with `replan_required=true` when a complete replan envelope is included. |
| `revise` | Generated package itself is incomplete and needs another correction pass — **not** “the prior strategy must be revised.” |
| `reject` | Reject the generated package. |
| `no_change` | No cognition alteration; `replan_required` must be false. |

Strategic invalidation is expressed through `replan_required` and the replan envelope, not through `overall_result=revise`.

These distinctions are semantic — not keyword triggers, regex classifiers, or event-type tables.

Identity is preserved when pursuit remains semantically the same. Lineage fields record supersede/parent relationships without becoming an execution graph.

---

## Lifecycle before #64

`active → inactive` is persistable. Destructive retirement (`retired` removed from current store) remains gated until #64 forensic preservation exists.

---

## Source snapshot

`CognitionUpdateSourceSnapshot` captures scope, contributors, prior revision, prior authority vector, current lineage targets, continuity versions, fingerprints, committed-move refs, catch-up mode, `semantic_authority_excerpts`, and bounded `prior_operative_cognition`.

Catch-up modes:

| Mode | Use |
|------|-----|
| `sequential` | Per-commit reconstruction when intermediate evidence exists |
| `endpoint_reconciliation` | Current state restorable but intermediate decisions missing; must record `evidence_gap` |

---

## Freshness algorithm (single session)

```text
if assimilated_authority missing → freshness_unprovable
else if commit lineage differs → semantic_assimilation_pending
else if cv matches → fresh
else recompute fingerprint:
  if unchanged → authority_generation_changed_unchecked
  else → semantic_assimilation_pending
```

---

## Model A status categories (#63 wiring)

`fresh`, `authority_generation_changed_unchecked`, `semantic_assimilation_pending`, `lineage_incomplete`, `shared_scope_ambiguous`, `freshness_unprovable`, `overlay_unavailable`

---

## Forensic handoff (ephemeral; #64 deferred)

Outcomes: `semantic_update`, `semantic_replan`, `semantic_no_change`, `objective_authority_unchanged`, `endpoint_reconciliation`

---

## Ownership

| #61 | #63 |
|-----|-----|
| Authority projection, fingerprint, contracts, objective validation, materialization, commit preconditions, freshness assessment | Trigger timing, model calls, retry orchestration, Model A gating |

| #61 | #64 |
|-----|-----|
| Ephemeral forensic handoff shapes | Durable decision journal |

---

## Replan transport envelope (#68)

Node (`plot-cognition-update-envelope.mjs`) performs **structural** transport normalization and validation only. Python/domain (`plot_cognition_update_contract.py`, `commit_update`) remains authoritative for objective cognition policy (activity-state legality, provenance, applicability, budgets, integrity, semantic grounding).

### Canonical replan proposal fields

When `replan_required=true`, the top-level inference envelope must include `replan_proposal` and `replan_evaluation` per existing schemas. The replan proposal uses canonical fields:

| Canonical field | Purpose |
|-----------------|--------|
| `proposal_id` | Replan proposal identity |
| `goals` | Replacement goal drafts |
| `pressures` | Replacement pressure drafts |
| `replan_rationale` | Why replan is warranted |
| `global_frame` | Optional replacement frame |

Each goal must include `goal_id`, `intended_direction`, `planning_horizon`, and `applicability`. Each pressure must include `pressure_id`, **`pressure_text`** (not `description`), `dramatic_rationale`, and `applicability`.

### Proposal-to-persistence bridge (#68 Part C)

Storyteller inference emits **semantic proposal items**; the persisted #58 overlay requires additional deterministic metadata. These layers are distinct:

| Layer | Owner | Contents |
|-------|-------|----------|
| **Model inference / transport** | Storyteller (#63) | Semantic fields only (`intended_direction`, `planning_horizon`, `pressure_text`, `dramatic_rationale`, applicability, optional basis notes) |
| **Deterministic enrichment** | Domain (`plot_cognition_proposal_enrichment.py`) | Fill-only stamps before validation: item `schema`, `creation_provenance.source = storyteller`, `activity_state = active` when absent |
| **Objective validation** | Domain (#61) | Full #58 overlay rules on enriched proposal |
| **Persisted overlay** | Domain (#59) | Complete cognition after materialization |

Enrichment is fill-only: explicit non-Storyteller provenance and explicit lifecycle values are preserved. Correction may request missing **semantic** transport fields; it must not request `schema`, `creation_provenance`, or `activity_state`.

### Supported top-level aliases (bounded, deterministic)

When canonical and alias are both present, **canonical wins** (aliases are not merged).

| Canonical | Supported alias |
|-----------|-----------------|
| `goals` | `proposed_goals` |
| `pressures` | `proposed_pressures` |
| `replan_rationale` | `proposal_rationale` |
| `proposal_id` | `replan_id` |
| `global_frame` | `proposed_global_plot_frame` |

Unsupported synonym fields are not generically coerced. Nested semantic fields (for example `description` → `pressure_text`) are **not** auto-normalized.

### Non-empty replan requirement

When `replan_required=true`, after alias normalization the replan proposal must contain **at least one** substantive goal and/or pressure meeting structural field requirements. Zero goals and zero pressures fails pre-finalize contract validation (`replan_required_empty_cognition`) and is eligible for bounded contract correction.

`replan_required=false` behavior is unchanged.

### Finalize failure distinction (#68)

Plot Cognition finalize/WAFI distinguishes:

1. **Forensic intent persistence failure** — intent chronicle could not be written (`forensic_persistence_failed`, stage `intent_persistence_failed`).
2. **Domain mutation rejection** — intent persisted; `commit_update()` rejected the proposal. Public response preserves domain `UpdateCommitResult.code` (for example `integrity_invalid`, `stale_revision`, `budget_exceeded`) with `forensic_stage=mutation_failed`. Not collapsed into `forensic_persistence_failed`.
3. **Forensic completion persistence failure** — mutation succeeded but completion chronicle failed (`forensic_persistence_failed`, stage `completion_persistence_failed`).

Successful finalize behavior is unchanged.
