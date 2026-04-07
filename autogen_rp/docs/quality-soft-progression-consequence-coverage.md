# [QUALITY] Under-classification of low-intensity progression (soft progression signals)

**Not a defect.** **QUALITY / COVERAGE GAP** — classifier sensitivity and coverage only. Status and any closure criteria are tracked on GitHub (see **Tracking** at the end of this file).

## Summary

Some structured moves that represent **real but low-intensity narrative progression** do not emit any `consequences` from the continuity classifier.

These cases do not break progression enforcement under current conditions, but represent a **coverage gap** in how subtle progression is detected.

## Context

During validation work around the progression retry instability fix:

- High-signal progression (e.g. spatial repositioning, refusal, stance shifts) is now correctly classified.
- However, certain moves still produce `consequences: []`.

Example characteristics:

- compliance-oriented intent (e.g. “fine”, “go ahead”, passive acceptance)
- mild or indirect movement
- no clear geometry shift
- no strong refusal / challenge signal

These were observed in cases like:

- session_383 turn-13–type moves (historical repro)
- similar low-intensity beats

## Why this is NOT a bug

- The system is behaving consistently with current rules: no strong structural change → no consequences.
- Progression enforcement is stable: long_session runs complete with 0 retries.
- No incorrect classification is occurring.

Therefore this is a **coverage / sensitivity gap**, not a failure.

## Problem framing

The current classifier emphasizes:

- geometry (REPOSITIONING)
- conflict stance (REFUSAL / AGREEMENT)
- explicit structural signals

But under-detects:

- subtle disengagement
- passive compliance that shifts dynamics
- low-energy interaction reconfiguration
- “soft” progression that still moves the scene forward

## Invariants for any classifier extension (reference)

If sensitivity were ever increased, these properties would need to remain true:

- deterministic behavior (no LLM)
- continuity as the single source of truth
- strict Q1 meaning (no inflation of trivial turns)
- stability of calm / low-action scenes

## Constraints

Do **not**:

- introduce fallback / synthetic consequence tags
- weaken progression enforcement
- classify purely cosmetic or observational turns as progression
- rely on narrator text or LLM interpretation

## Illustrative design space (non-prescriptive)

Examples of directions discussed in reviews (not commitments):

- refined intent interpretation for compliance-with-shift
- detection of interaction-state drift without geometry change
- controlled expansion of consequence categories (if needed)
- multi-signal inference from goal + tactic + dialogue (still deterministic)

## Success metrics (reference)

Dimensions by which an eventual change could be judged (not a local checklist):

- increased coverage of subtle progression cases
- **no** increase in false positives in calm scenes
- **no** broad inflation of Q1 qualification rate
- existing progression stability tests still pass (long_session, etc.)

## Notes

During the progression-retry fix, classifier scope stayed narrow so that consequence detection did not add noise or drift relative to enforcement behavior.

See also: [`../python/rp_app/ARCHITECTURE.md`](../python/rp_app/ARCHITECTURE.md) (*Progression enforcement vs continuity classification*).

## Tracking

This item is tracked in GitHub: https://github.com/KizzieFae/Holy_Grail_RP/issues/23

This document is reference-only and does not act as a task tracker, backlog, or checklist. Status, ownership, and completion steps belong on the GitHub issue only.
