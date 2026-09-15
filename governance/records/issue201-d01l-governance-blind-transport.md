# Issue #201 — D-01-L Governance Blind Sequence Evaluation Transport

**Purpose:** Independent Governance blind scoring for D-01-L longitudinal synchronous-preamble Storyteller test.

## Causal question

Does synchronous preamble Storyteller cognition add material multi-turn narrative value when Plot cognition and post-commit Storyteller cognition remain available?

## Transport package (safe to upload — no answer key)

1. `governance/records/issue201-stage2-human-evaluator-worksheet.md` — scenario briefings + per-turn rubric reference
2. `data/investigation_runs/issue201-package-d-d01l-2026-09-14T22-12-05-873Z/outputs/issue201-d01l-blind-sequence-packet.json`

## Do NOT transport

- `issue201-d01l-blind-sequence-answer-key.json`
- `issue201-package-d-d01l-longitudinal-report.json`
- Sequence JSON sidecars, branch logs, inference/latency metadata
- Any arm / Storyteller / session identifiers

## Instructions

- **8 complete sequences**, labels `SEQ-A` … `SEQ-H` (shuffled)
- **Primary endpoint:** 10 sequence-level dimensions (1–5 per sequence) — see packet `sequence_level_dimensions`
- **Secondary endpoint (optional, separate):** per-turn 11-dimension rubric — do not composite with primary
- Evaluate each **complete chronological sequence** as the unit of analysis
- Lock all primary scores before requesting answer-key decode
- Execution record: `governance/records/issue-201-package-d-d01l-execution-2026-09-14.md`

## Post-scoring decode

After locked scoring, Governance may request the answer key for between-arm causal comparison per pre-registered rules in `governance/records/issue-201-package-d-d01l-consensus-refinement-2026-09-14.md`.
