# Issue #201 LH-0 — Final Semantic Qualification Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Remediation candidate:** `b7d5b7cbecae443d4b308011edbec851e691994d`  
**Final qualification run:** `data/investigation_runs/issue201-lh0-final-qualification-2026-09-15T22-17-52-827Z`  
**LH-1A:** NOT authorized  

---

## Prior evidence anchors (preserved)

1. First live — `issue201-lh0-live-2026-09-15T21-16-16-968Z`
2. Remediation corrective — `issue201-lh0-live-2026-09-15T21-36-09-178Z`
3. C/D post-fix — `issue201-lh0-cd-postfix-2026-09-15T21-51-52-447Z`
4. **This final qualification tranche**

---

## Remediation delivered (`b7d5b7c`)

| Track | Change |
|-------|--------|
| C/D merge | `storyteller_round_packaging.py` merges `finalized_projection` arm-neutrally (no Plot overlay required) |
| Semantics | Fixture `semantic_content` + `causal_design`; model-facing text is narrative policy, not bookkeeping IDs |
| Deferred timing | `obligationsForConsumer` projects only when activation predicate satisfied |
| Evidence | Decision-fork classes, semantic receipt adequacy, LH-A counterfactual, strengthened E/F/G/H adjudication |
| Validation | `runLh0SemanticValidationSuite()` — 28/28 PASS before live run |

---

## Final qualification A–J matrix

| Arm | Sequence | A | B | C | D | E | F | G | H | LH-1A |
|-----|----------|---|---|---|---|---|---|---|---|-------|
| LH-A (control) | `LH0-LIVE-lh_a-1789510672831` | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | n/a |
| LH-B | `LH0-LIVE-lh_b-1789510949034` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |
| LH-C | `LH0-LIVE-lh_c-1789511414841` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |
| LH-D | `LH0-LIVE-lh_d-1789511811619` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |

\*LH-A is counterfactual control; persistent-arm criteria marked pass by design (no persistent obligations).

---

## Key findings

### Seam remediation succeeded

- **C/D consumer receipt** now passes (was blocked at D in post-fix run).
- **Semantic payloads** reach Character manifest at receipt turns (e.g. T6 LH-B/C/D samples include guest-policy semantics).
- **Deferred withhold** works: no character receipt T1–T4; first receipt at T6 when `character_due_count: 2`.

### E/F/H remain unproven — timing alignment defect

- Guest-policy **decision fork is T5**; first semantic receipt is **T6** on all persistent arms.
- At fixture T5, `character_due_count: 0` because `prepareLh0RoundTransport` uses continuity `cognitionTurnIndex` (≈4) rather than harness `lh0FixtureTurnIndex` (5).
- Character did not receive obligations at the authored fork turn; E/F/H failures are **not** fair cognition adjudication yet.
- Counterfactual: LH-A and persistent arms all show `same_outcome_or_indeterminate` at both forks.

### K6

Detected; does not block execution or semantic obligations. Independently reportable.

---

## Bounded next work (Governance)

1. Wire `lh0FixtureTurnIndex` into `prepareLh0RoundTransport` (one-line orchestration fix).
2. Re-run **one** qualification tranche OR targeted T5 receipt verification — **not** executed under this authorization.

---

## Governance decision required

LH-0 transport/semantics instrument is substantially improved but **LH-0 is not complete** and **LH-1A is not ready** until receipt aligns with decision-fork turns and E/F/H can be fairly adjudicated.
