# Plot Cognition Forensic Chronicle contract (#64)

Normative contract for the Domain-owned **Plot Cognition Forensic Chronicle**. Operational Plot Cognition truth remains in the Overlay (#59); this store is append-only historical semantics for investigators.

## Authority split

| Store | Role |
|-------|------|
| Continuity | World truth |
| Plot Cognition Overlay (#59) | Current operational cognition |
| DSH execution evidence | Assembled request / provider response |
| Chronicle (#64) | Historical semantic decisions and mutation forensics |
| Derived indexes | Rebuildable navigation only (non-authoritative) |

Chronicle data must **never** be consumed by normal role-context assembly or packaging.

## Logical identity and layout

- **Scope key:** `plot_cognition_scope_id`
- **Root:** `data/plot_cognition_forensics/{plot_cognition_scope_id}/`
- **Authoritative:** `records/*.json` (append-only), `content/*.json` (deduplicated semantic artifacts)
- **Derived:** `index.json`, `scope_manifest.json` (rebuildable / correlation)

```
data/plot_cognition_forensics/{plot_cognition_scope_id}/
  scope_manifest.json
  index.json
  records/{record_id}.json
  content/{artifact_id}.json
```

## Record classes (M / D / O / I)

| Class | `record_class` | Durability |
|-------|----------------|------------|
| **M** mutation-bearing | `operational_mutation` | WAFI intent → overlay CAS → WAFI completion |
| **D** non-mutating semantic | `semantic_decision`, `consumer_decision` | Durable decision before finalize/bind success |
| **O** reconstructable observation | reference-only in payload | Only when another authoritative artifact fully preserves meaning |
| **I** integrity | `integrity` | Gaps, incomplete WAFI, missing evidence — never fabricated semantics |

## WAFI (mutation-bearing)

1. **Intent** — persist full semantic package + prior revision before operational mutation.
2. **Mutation** — existing Overlay CAS services (Chronicle is not the executor).
3. **Completion** — persist resulting revision + bounded snapshot; finalize must not report success until completion is durable.

Post-commit pending-work recording (`record_plot_cognition_post_commit`) uses the same WAFI ordering via `wafi_record_post_commit_pending_work`. Lifecycle finalize paths that clear pending work do so inside the WAFI completion snapshot hook so the completion record captures the cleared state.

Failure behavior:

- Intent persistence failure → no mutation.
- Mutation failure → intent preserved; no completion fabricated.
- Completion persistence failure → finalize reports failure; incomplete WAFI detectable on restart.

**Replay / reconciliation:** On scope activation, `reconcile_incomplete_wafi()` emits integrity records for intent-without-completion pairs. HTTP retries with the same idempotency key must not double-apply overlay mutations (completion short-circuit + overlay CAS).

## Semantic artifact capture

Bounded verbatim capture at decision time (not digest-only, not later Continuity recompute):

- Authority projection (`capture_authority_projection_verbatim`)
- Bounded overlay snapshots (`bounded_overlay_snapshot`)
- Epistemic envelopes where required for Layer B reconstruction

Truncation limits are recorded in artifact `truncation_policy` metadata.

## Execution evidence cross-reference

Chronicle references DSH execution evidence by stable `evidence_id` in `inference_evidence_refs`. The session execution-evidence index exposes a derived `plot_cognition` navigation bucket (`hg_plot_cognition_forensics_index_v1`) — rebuildable, not authoritative.

## Orchestration and Layer B reuse forensics (#166)

Pure orchestration decisions that never enter a mutation lifecycle (for example `plan → none`) record **`semantic_decision`** via `POST /v1/plot-cognition/orchestration/record-gate` with `mutation_lifecycle_entered: false`. Do not fabricate WAFI mutation intent/completion for no-work paths.

Layer B reuse records **`consumer_decision`** on `projection_evaluate` with payload distinguishing:

| `decision` | Meaning |
|------------|---------|
| `invoke` | Fresh Layer B evaluation required (cache miss or regeneration) |
| `reused` | Prior evaluation reused; includes `reuse_key_digest` and `prior_inference_evidence_id` |

These observability records are non-authoritative and must remain reconstructable alongside DSH execution evidence.

## Runtime privilege boundary

Modules that assemble Character / Storyteller / DSH role context must not import Chronicle repositories or services. Investigator tooling under `tools/investigation/` is the intended reader.

## Pre-#64 activation baseline

First Chronicle touch for a scope with existing Overlay state writes `chronicle_activation` (integrity / `history_unavailable`) with bounded operational snapshot. No synthetic initialization/update/replan history is emitted.

## #59 retirement prerequisite

`PlotCognitionForensicsService.forensic_preservation_satisfied(scope_id, cognition_item_id=..., idempotency_key=...)` returns true only when a durable WAFI completion exists with preserved prior semantic state for the item. #64 does **not** enable destructive retirement by itself.

## #64 / #65 boundary

#64 delivers chronicle durability, WAFI, investigator views, and preservation predicates. Operational tuning, compaction, and advanced reconciliation policy belong to #65+.

## Investigator workflow

```bash
python tools/investigation/trace_plot_cognition_forensics.py <plot_cognition_scope_id> timeline
python tools/investigation/trace_plot_cognition_forensics.py <scope> commit <domain_commit_id>
python tools/investigation/trace_plot_cognition_forensics.py <scope> integrity
python tools/investigation/trace_plot_cognition_forensics.py <scope> layer_b <batch_id> --session <hg_session_id>
```
