# [QUALITY] Under-classification of low-intensity progression (soft progression signals)

## Summary

Some structured moves that represent **real but low-intensity narrative progression** do not emit any `consequences` from the continuity classifier.

These cases do not break progression enforcement under current conditions, but represent a **coverage gap** in how subtle progression is detected.

## Context

During validation of the progression retry fix:

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

## Goals (future work)

Improve detection of **soft progression signals** while preserving:

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

## Potential directions (non-binding)

- refined intent interpretation for compliance-with-shift
- detection of interaction-state drift without geometry change
- controlled expansion of consequence categories (if needed)
- multi-signal inference from goal + tactic + dialogue (still deterministic)

## Acceptance criteria

A future solution should:

- increase coverage of subtle progression cases
- **not** increase false positives in calm scenes
- **not** inflate Q1 qualification rate broadly
- pass existing progression stability tests (long_session, etc.)

## Priority

Low (post-stability / refinement phase)

## Notes

This issue was intentionally deferred during the progression retry fix to avoid introducing noise or weakening enforcement logic.

See also: [`../python/rp_app/ARCHITECTURE.md`](../python/rp_app/ARCHITECTURE.md) (*Progression enforcement vs continuity classification*).

## Tracking

This item is tracked in GitHub: https://github.com/KizzieFae/Holy_Grail_RP/issues/23

This document is reference-only and does not act as a task tracker.
