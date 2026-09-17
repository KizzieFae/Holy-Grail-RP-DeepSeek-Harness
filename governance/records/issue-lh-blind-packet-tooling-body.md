## Summary

The long-horizon blind packet builder (`buildLh1aBlindPacket` in `v2/rp_runtime/scripts/lib/issue201-lh1a-blind-packet.mjs`) emits a placeholder `presentation_text` string instead of actual presentation evidence from live execution artifacts. This is an independent tooling defect discovered during LH-1A apparatus work and must be repaired before future LH-1B/LH-2 blind-secondary evaluations rely on packet builders.

## Type

quality

## Layer

other

**Justification:** Offline investigation/tooling under `v2/rp_runtime/scripts/lib/`; not runtime orchestration or continuity. **Intended final Layer:** `other` (harness tooling).

## Pattern status

single_instance

## Current status

open

## Evidence (mandatory)

- **Scenario id:** `ayame_household_entry_evaluation` (LH-1A campaign)
- **Audit session path:** `data/investigation_runs/issue201-lh1a-live-campaign-2026-09-16T02-25-55-261Z/`
- **Turn index:** n/a — defect is in packet builder source, not a single live turn

## Evidence (preferred)

`issue201-lh1a-blind-packet.mjs` line 20:

```javascript
presentation_text: '[presentation recorded at live execution — apparatus validation uses policy stimuli only]',
```

LH-1A blind evaluation proceeded because the evaluable packet was independently rebuilt from sequence artifacts, integrity-checked, hashed, scored, and locked before decode. **This defect does NOT invalidate the locked LH-1A blind evaluation.**

## Expected behavior

Post-live blind packet construction should ingest actual presentation evidence from sequence execution artifacts (or an equivalently authoritative rebuild path) and must fail closed if presentations are missing, stubbed, or placeholder-only.

## Observed behavior

`buildLh1aBlindPacket` hardcodes placeholder presentation text for every turn regardless of available live evidence.

## Deterministic reasoning

Blind evaluators cannot score presentation-dependent dimensions from stub text. A regression test must prevent placeholder packets from being mistaken for evaluable packets.

## System impact

Future long-horizon blind-secondary campaigns (LH-1B optional, LH-2) could be scored on non-evidence if this builder is used without manual rebuild.

## Constraints

- Generalize appropriately for LH-1B/LH-2 packet construction (not LH-1A-only hack).
- Do not alter locked LH-1A blind scores or decode state.
- Regression test required.

## Affected modules

- `v2/rp_runtime/scripts/lib/issue201-lh1a-blind-packet.mjs`
- Future generalized long-horizon packet builder (if split from LH-1A module)
- Related tests under `v2/rp_runtime/tests/`

## Validation criteria

- Unit/integration test: builder rejects or fails when presentations are placeholder-only.
- Unit/integration test: builder includes real presentation text when artifacts supply it.
- Document rebuild vs builder authority for blind evaluation chain of custody.

## Documentation

- [ ] Documentation reviewed and updated where behavior or contracts changed

## Workflow weight

standard

## Chain of custody

- Parent umbrella: Issue #201 (long-horizon persistent narrative cognition)
- Discovered during LH-1A blind packet preparation
- LH-1A locked evaluation unaffected (independent artifact rebuild path used)
