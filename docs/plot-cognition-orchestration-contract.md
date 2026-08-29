# Plot Cognition Runtime Orchestration Contract (#63)

Normative orchestration contract for Storyteller Plot Cognition runtime activation. This document records the agreed **Domain prepare → DSH infer → Domain finalize** model. It does not redefine #58–#62 overlay, initialization, update/replan, or projection safety contracts.

## Staged orchestration model

| Phase | Owner | Mutates continuity? | Calls inference? |
|-------|-------|---------------------|------------------|
| **Prepare** | Domain | No (read-only assembly) | No |
| **Infer** | DSH | No | Yes (bounded, phase-specific) |
| **Finalize** | Domain | Only when phase owns mutation (init/update/replan commit) | No |

Production Character projection **must not** use a synchronous Python→DSH evaluator callback inside `project_character_candidates()`. Tests may still use `DeterministicRuleBasedEpistemicEvaluator` for regression.

## Phase ownership

| Lifecycle | Prepare endpoint | Finalize endpoint | Domain mutation |
|-----------|------------------|-------------------|-----------------|
| Initialization | `POST /v1/plot-cognition/init/prepare` | `POST /v1/plot-cognition/init/finalize` | Initial overlay commit when absent |
| Update | `POST /v1/plot-cognition/update/prepare` | `POST /v1/plot-cognition/update/finalize` | Overlay update commit |
| Replan | `POST /v1/plot-cognition/replan/prepare` | `POST /v1/plot-cognition/replan/finalize` | Replan overlay commit |
| Character advisory generation | `POST /v1/plot-cognition/advisory-generation/prepare` | `POST /v1/plot-cognition/advisory-generation/finalize` | None (returns validated candidates) |
| Character projection evaluation | `POST /v1/plot-cognition/projection/prepare` | `POST /v1/plot-cognition/projection/finalize` | None (renders approved contributions) |
| Regeneration | second prepare/finalize on regenerated candidate | same projection endpoints | None |

Freshness assessment: `POST /v1/plot-cognition/freshness/assess`.

## Split-phase Character projection

- `prepare_character_projection_batch()` — Layer A structural eligibility, evaluation budget, bounded epistemic envelopes, evaluator manifests, binding digest.
- `finalize_character_projection_batch()` — consumes supplied parsed semantic results only; applies #62 verdict semantics; surfaces `pending_regenerations` on `rewrite_required`; enforces projection budget; emits forensic handoff.
- Stale or unknown prepared batches **fail closed**.
- Max regeneration attempts per candidate: **1**. Max semantic evaluations per candidate path: **initial + one reevaluation**.

## Semantic epistemic context

`CharacterEpistemicContextEnvelope` separates:

**Semantic material (bounded text):** known committed events, exposable basis summaries, scene-visible facts, permitted own-card material, candidate text, epistemic-prohibition instructions.

**Identity/freshness evidence:** `known_by_snapshot_id`, authority fingerprint, overlay revision, visibility digest, round/turn/binding, lineage.

Hashes and IDs are **not** substitutes for semantic material. Withheld basis appears structurally (IDs/categories/reasons), not as hidden prose.

### Regeneration authority (#66)

Production Character projection regeneration is **Domain-authorized**:

| Step | Endpoint | Owner |
|------|----------|-------|
| Register first/second semantic result | `POST /v1/plot-cognition/projection/register-semantic-result` | Domain |
| Authorize regeneration + manifest | `POST /v1/plot-cognition/projection/regeneration/prepare` | Domain |
| DSH advisory regeneration infer | `character_advisory_generation` (DSH) | DSH |
| Validate regenerated candidate | `POST /v1/plot-cognition/projection/regeneration/finalize` | Domain |
| Finalize once per batch | `POST /v1/plot-cognition/projection/finalize` (`use_registered_results: true`) | Domain |

DSH orchestrates inference only; Domain owns batch membership, regeneration eligibility, guidance validity, and finalize-once Chronicle gating. Node must not supply unregistered regeneration guidance.

Pre-finalized projection contributions are transported to Character context via `plot_cognition_finalized_projection` on `ContextPrepareRequest`. Storyteller packaging **must not** re-finalize these contributions. Character move retries reuse the same finalized projection for the turn binding.

Prepared batch runtime state is **transient**. Domain process loss abandons the attempt; execution evidence is forensic only and cannot bypass a new Domain binding.

### Regeneration (legacy test path)

Tests may still call `finalize_character_projection_batch()` directly with `regeneration_inputs` and `second_pass_results` after supplying semantic results inline.

## Candidate provenance paths

1. **Model A** — round-local package/item lineage; not blended into overlay generation.
2. **Character-scoped overlay** — deterministic extraction from intended-direction text; still requires full Layer B.
3. **Global/frame-derived** — DSH-generated independently phrased candidates with lineage; never direct projection of raw global cognition.

All paths converge only at the prepared Character projection batch.

## Pending-work authority

Post-authoritative-commit, Domain records `PlotCognitionPendingWork` on the overlay store (`pending_work`). DSH may cache scheduling pointers but is **not** the authority. Pending work survives overlay reload.

### DSH post-commit scheduling (#63)

Production round orchestration (`hg-round-orchestrator/service.mjs`) invokes `runPostCommitPlotCognitionLifecycle` after each successful Character commit (parallel to Narrator, joined before the next turn). At round start, `runPlotCognitionPendingWorkLifecycle` re-discovers outstanding work from Domain state only (resume-safe across orchestrator restart).

Routing uses `POST /v1/plot-cognition/pending-work/plan` (#61 freshness semantics):

| Plan operation | DSH action |
|----------------|------------|
| `none` / `clear_pending` | Skip or clear stale pending flag |
| `reconciliation` | Domain finalize (no inference) |
| `authority_advance` | Domain finalize (no inference) |
| `initialization` | Init prepare → infer → finalize |
| `semantic_update` | Update prepare → infer → finalize (+ replan when `replan_required`) |
| `blocked` | Pending preserved; freshness barrier withholds overlay |

Implementation modules: `plot-cognition-orchestration.mjs`, `plot-cognition-update-substrate.mjs`.

## Next-consumer freshness barrier

When pending Plot Cognition work exists:

- **Character:** withhold overlay-derived advice until fresh.
- **Director:** withhold stale overlay slice; Model A may continue.
- No warning/banner exposure of stale strategic cognition.
- Prepared projection batches fail closed on stale binding.

## Layer B concurrency

Production Layer B evaluation is **sequential** for #66 (`plot-cognition-character-projection.mjs`). Bounded parallel evaluation remains **#65** ownership; do not enable `max_parallel_epistemic_evals` in production wiring until #65 certifies a baseline.

## Layer B failure semantics

Provider failure, timeout, malformed result, or missing evaluator → affected candidates **withhold** (`evaluator_unavailable`). No deterministic semantic authorization fallback.

## Budgets and concurrency

Orchestration ceilings live in `StorytellerOrchestrationPolicy` (generated candidates, context items/chars, parallel evals, regeneration attempts). #62 `ProjectionBudget` still governs evaluation/projection candidate counts. Layer B evaluations may run in bounded parallel after Layer A; finalize order is deterministic.

## Forensic propagation (#63 → #64)

#63 propagates reconstructability via `ProjectionForensicHandoff` and phase forensic payloads. No durable forensic store in #63 (#64 owns persistence).

## Boundary

| Issue | Owns |
|-------|------|
| #63 | Orchestration seams, prepare/finalize APIs, freshness barrier, packaging integration |
| #64 | Durable forensic storage |
| #65 | Performance tuning/benchmarking |

## Implementation modules

- `v2/domain_api/plot_cognition_orchestration_contract.py`
- `v2/domain_api/plot_cognition_projection_batch.py`
- `v2/domain_api/character_epistemic_projection_context.py`
- `v2/domain_api/plot_cognition_orchestration_service.py`
- `v2/domain_api/plot_cognition_orchestration_api.py`
- `v2/domain_api/plot_cognition_lifecycle_api.py`
- `v2/rp_runtime/src/lib/plot-cognition-orchestration.mjs`
- `v2/rp_runtime/src/lib/plot-cognition-update-substrate.mjs`
- `v2/rp_runtime/src/plugins/hg-phase-executors/plot-cognition-character-projection.mjs`
- `v2/domain_api/plot_cognition_projection_runtime.py`
