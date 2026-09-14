# Issue #197 — Consensus Challenge Record

**Date:** 2026-09-14  
**Issue:** [#197](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/197)  
**Git SHA:** `79cdb5a`  
**Phase:** Full-weight consensus challenge/refinement (no implementation)

## Governing invariant (evaluated)

> Uniform projection is an optimization, not the general correctness path. It may be selected only when the system has positively established that the Player contribution is uniformly projectable to all relevant viewers. Any unresolved semantic uncertainty or disagreement must fall back to full PVR decomposition.

**Compatibility assessment:** **Compatible** with #90/#91/#121/#124/#155 contracts **as written**, but **not with current runtime behavior**. Architecture docs already describe triage as routing-only, fail-closed to `full_pvr`, and state checker `reason` is audit-only. The defect is that a single affirmative boolean is treated as sufficient positive establishment without independent semantic evidence.

## Recommended architecture

**Architecture E (Hybrid)** — see full report sections K–L.

Core contract:

1. **Semantic layer** proposes uniformity (triage; optionally strengthened prompt).
2. **Semantic verification layer** (affirmative-only, adversarial rubric) independently challenges affirmative proposals.
3. **Deterministic policy layer** permits `uniform_projection` only on `triage_affirmative AND verification_pass`; all other outcomes → `full_pvr`.

No calibrated confidence bypass. No lexical enforcement. Corpus remains certification-only.

## Evidence disposition

| Artifact | Disposition |
|----------|-------------|
| `issue-197-investigation-2026-09-14.json` | **Committed** as investigation evidence |
| `issue-197-investigation-2026-09-14.md` | **Committed** as investigation evidence |
| This record | **Committed** as challenge/refinement evidence |

## Consensus readiness

**READY FOR GOVERNANCE CONSENSUS DECISION** (architecture refined; implementation not authorized).
