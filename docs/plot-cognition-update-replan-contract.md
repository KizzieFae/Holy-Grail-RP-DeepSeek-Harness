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

Excluded: presentation-only history, skip/audit metadata, rejected B2, K2 occurrence duplicates of already-represented public events.

Fingerprint: stable JSON serialization → SHA-256 (same pattern as #60).

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

Identity is preserved when pursuit remains semantically the same. Lineage fields record supersede/parent relationships without becoming an execution graph.

---

## Lifecycle before #64

`active → inactive` is persistable. Destructive retirement (`retired` removed from current store) remains gated until #64 forensic preservation exists.

---

## Source snapshot

`CognitionUpdateSourceSnapshot` captures scope, contributors, prior revision, prior authority vector, current lineage targets, continuity versions, fingerprints, committed-move refs, and catch-up mode.

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
