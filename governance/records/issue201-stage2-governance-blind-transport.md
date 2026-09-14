# Issue #201 — Governance AI Blind Evaluation Transport (no answer key)

**Purpose:** Enable independent second semantic evaluation by Governance AI without decoding architecture identity.

## Transport package (safe to upload)

1. `governance/records/issue201-stage2-human-evaluator-worksheet.md` — rubric + scenario briefings + instructions  
2. `governance/records/issue201-stage2-human-evaluator-scoring-sheet.md` — all 16 blind samples (labels A–P only)  
3. `data/investigation_runs/issue201-package-d-stage2-2026-09-14T08-09-42-791Z/outputs/issue201-stage2-human-blind-eval-packet.json` — machine-readable blind packet (presentation_text only per sample)

## Do NOT transport

- `issue201-stage2-human-blind-eval-answer-key.json`  
- `issue201-package-d-stage2-tranche1-report.json`  
- Any `*-meta.json` with `experiment_id` or `round_options`  
- Latency / inference summaries

## Governance AI instructions

- Score the 11 semantic dimensions (1–5) per sample using the rubric.  
- Use scenario briefings to select Arkham vs Ayame context per presentation.  
- Do not infer control vs ablation or experiment identity.  
- Report scores only; do not compare to Implementation-AI scores until human primary scoring is locked.  
- Sample **N** has empty presentation (failed round) — score N/A or note "no player-visible output."

## Primary evaluator

Project user scores first using the same artifacts; Governance second pass is optional and deferred until primary sheet is complete.
