# Issue #201 — R5 runner integration and qualification (2026-09-17)

## Summary

Minimal **R5-A1 / R5-B1** sequences were wired into the authoritative **LH-1B live turn path** (`runLh1bTurn` / `runA2BeatRound`) with mock inference profiles and execution evidence. A full **28-turn** mock qualification run completed.

**Real-runner qualification: FAIL (fail-closed).** Apparatus **G1–G8** on canonical snapshots still **PASS**.

### Primary blocker (RG3)

At **R5-A1 T14**, the assembled Character request includes the house-specific meal-location rule in **`recent_scene_transcript`** (`transcript_sufficient = true`). Marker hits include `pantry alcove`, `not at the household dining table`, `trial week`. The rule was committed at **T6** and remains inside the production transcript window at T14.

No retrieval, Continuity, memory/summary, or decision-stimulus leakage was required to explain availability on A1; **transcript alone is sufficient**.

### Secondary gates

| Gate | Result |
|------|--------|
| RG1 shared establishment | PASS (after combined move+presentation phrase check) |
| RG2 persistence entailment | PASS |
| RG3 A1 lean absence | **FAIL** — transcript_sufficient |
| RG4 B1 persistence-only | **FAIL** — persistence present but not unique vs transcript |
| RG5 stimulus neutrality | PASS |
| RG6 discriminability | PASS |
| RG7 R0→R5 chain | **FAIL** — R4 without R5 (`substrate_explained`) |
| RG8 A/B lean parity | **FAIL** — lean hash mismatch (incidental memory timestamps / perceptual inventory counts; same T6 dialogue in both transcripts) |

**Live R5-A1/B1 not authorized.**

## Evidence

- `data/investigation_runs/issue201-r5-runner-qualification-2026-09-17/`
  - `r5_runner_qualification.json`
  - `r5_sequences/R5-A1/sequence_result.json`
  - `r5_sequences/R5-B1/sequence_result.json`

## Code entry points

- `v2/rp_runtime/scripts/lib/issue201-r5-live-lib.mjs` — `executeR5MockSequence`
- `v2/rp_runtime/scripts/lib/issue201-r5-runner-qualification-lib.mjs` — `runR5RunnerMockQualification`
- `node v2/rp_runtime/scripts/issue201-r5-seam-verification.mjs --runner-qualify`

## Frozen hashes (unchanged)

- Fixture: `896377dcc6a6cd1de9e92db262fb65c7cffb66f7764b8eddc4a47498d67d4068`
- Policy: `bbf280f06a57466709e351ce57a86ea9188dfc63e70624a3752dceb66dfadc82`
- Causal design: `26abbc25a866e52ca31b6caba49be614560b37bdc4a589f4128841d38d569b13`

## Governance next step

Decide whether to **revise horizon/transcript policy** (frozen experiment change), **accept architectural null result** (transcript already performs long-horizon recall), or **design a different fork** — do not suppress transcript or alter frozen stimuli under current #201 authorization.
