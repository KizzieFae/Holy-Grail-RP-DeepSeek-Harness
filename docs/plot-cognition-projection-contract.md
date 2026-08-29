# Plot Cognition consumer projection contract

**Status:** Normative projection contract — Issue **#62**  
**Semantic contract:** [plot-cognition-overlay-contract.md](./plot-cognition-overlay-contract.md) (#58)  
**Update/replan contract:** [plot-cognition-update-replan-contract.md](./plot-cognition-update-replan-contract.md) (#61)  
**Executable binding:** `v2/domain_api/plot_cognition_projection_*.py`  
**Parent program:** Issue **#48**

Defines how persistent Plot Cognition Overlay cognition and transient Model A advisory cognition are safely projected to Director and Character consumers. Orchestration (#63), durable forensic storage (#64), and production tuning (#65) are out of scope.

---

## Purpose

Globally informed Storyteller cognition must not leak into Character prompts. #62 establishes:

- shared projection infrastructure with consumer-specific profiles;
- Director globally informed advisory projection;
- Character two-layer safety (structural Layer A + semantic Layer B);
- bounded evaluation and projection budgets;
- forensic handoff envelopes;
- contract-level refresh/invalidation predicates.

---

## Authority boundary

| Concern | Owner |
|---------|--------|
| Authoritative world truth | **Continuity** |
| Advisory overlay cognition | **Plot Cognition Overlay** (#58–#61) |
| Round-local assessment | **Model A** |
| Projection gates and outcomes | **#62** (this contract) |
| Candidate generation / regeneration scheduling | **#63** |
| Durable forensic storage | **#64** |

Projection remains **advisory**. No projection path may write Continuity or enact moves.

---

## Director lane

Director may receive:

- active `GlobalPlotFrame`;
- global and scoped `PlotGoal` items;
- `UnresolvedNarrativePressure` items;
- valid Model A advisory material.

Director projection is globally informed subject to existing validity and authority boundaries.

---

## Character lane

Character projection uses:

1. **Layer A — deterministic structural eligibility** using applicability, basis-ref resolution, `known_by_snapshot`, provenance, and authority projection inputs from #58–#61.
2. **Candidate composition boundary** — only `CharacterAdvisoryCandidate.text` is semantically exposable.
3. **Layer B — subordinate semantic epistemic-leakage evaluation** on candidate text only.
4. **Bounded evaluation** before Layer B.
5. **Bounded projection** after semantic approval and any externally supplied regeneration.

### Hard rules

- `GlobalPlotFrame` is **never** directly projected to Character.
- Global `PlotGoal` / global pressure objects are **never** directly projected to Character.
- Frame- or global-goal-informed Character advice must arrive as an independently supplied `CharacterAdvisoryCandidate` with lineage and pass the full Character safety path.
- `projected_prospective` requires Layer B **pass**. Basis withholding alone is not a bypass.
- Model A Character projection requires structural `character_scope` evidence; substring/name matching is forbidden.

---

## Layer B semantic evaluator

Question: does proposed Character-facing advisory text communicate or materially imply information outside the Character's permitted epistemic envelope?

Verdicts:

| Verdict | Meaning |
|---------|---------|
| `pass` | Safe to project (subject to budgets) |
| `withhold` | Fail closed |
| `rewrite_required` | #63 may supply one regenerated candidate |
| `evaluator_unavailable` | Fail closed |

Layer B must **not** decide Continuity truth, establish Character knowledge, create facts, authorize structurally forbidden basis, perform general Storyteller QA, or author replacement prose.

---

## Boundedness

### Evaluation budget

Structurally admissible candidates are deterministically ordered and truncated to caller-supplied `max_evaluation_candidates`. Excluded items are recorded as `evaluation_budget_excluded`.

### Projection budget

Semantically approved candidates (after optional single regeneration) are deterministically ordered and truncated to `max_projection_candidates`. Excluded items are recorded as `projection_budget_excluded`.

No semantic importance scoring. Numeric tuning belongs to #63/#65.

---

## Regeneration boundary

#62 allows at most **one** regeneration attempt following `rewrite_required`. #63 owns generative retry. The contract records:

- original candidate;
- evaluator finding;
- regenerated candidate (when supplied);
- second evaluator result.

If regeneration is unavailable or the regenerated candidate still fails, projection fails closed.

---

## Forensic handoff

Distinct outcomes include:

`structurally_ineligible`, `evaluation_budget_excluded`, `semantic_pass`, `semantic_withhold`, `semantic_rewrite_required`, `semantic_evaluator_unavailable`, regeneration states, `projected_full`, `projected_prospective`, `projection_budget_excluded`.

Evidence must include semantic text sufficient to reconstruct source cognition, target Character, structural inputs, exposable basis, original/regenerated/final text, evaluator rationale, and lineage.

---

## Refresh / invalidation predicates

Reprojection is required when any of these change:

- overlay revision;
- authority fingerprint;
- Character `known_by_snapshot`;
- cognition lifecycle / applicability;
- semantic replan / supersession;
- Model A invalidation / replacement;
- incompatible packaging binding context.

Scheduling belongs to #63.

---

## Executable modules

| Module | Role |
|--------|------|
| `plot_cognition_projection_contract.py` | Normative types and envelopes |
| `plot_cognition_projection_semantic_safety.py` | Layer B interface |
| `plot_cognition_projection_service.py` | Layer A + projection orchestration |
| `storyteller_packaging_mapper.py` | Model A Character hard cutover |
| `storyteller_round_packaging.py` | Round-local packaging integration |

---

## Downstream ownership

| Issue | Owns |
|-------|------|
| **#62** | Projection contract, gates, budgets, forensic handoff, invalidation predicates |
| **#63** | Orchestration, generative candidates, regeneration scheduling |
| **#64** | Durable forensic storage/indexing |
| **#65** | Production tuning / performance |
