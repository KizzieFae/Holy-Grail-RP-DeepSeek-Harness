# Issue #124 / PR #127 — Final Forensic Hardening

**Date:** 2026-09-05  
**Behavioral HEAD:** `c70aab147f70141f634bc0bb9d88c98fa706c0b7`  
**Prior Greptile anchor:** `0d2b3124e769f9a150fe1d6637e3413120c59be2` (5/5 — superseded for behavioral review)

## Remediation scope

1. **Terminal `sir_malformed`:** persist `raw_semantic_output` in PVR `generation` on terminal DSH parse failure.
2. **Direct linkage:** persist `evidence_id` in PVR `generation` wherever execution evidence returns one.

Deferred: explicit `authority:` component labels (#124-only convention).

## Files changed (behavioral)

| File | Change |
|------|--------|
| `v2/rp_runtime/src/plugins/hg-phase-executors/player-decomposition-phase.mjs` | `buildInferenceGenerationForensics`, `attachInferenceEvidenceToDecomposition`; all generation paths include `evidence_id`; terminal `sir_malformed` includes `raw_semantic_output` |
| `v2/rp_runtime/tests/player-decomposition-phase.test.mjs` | Terminal malformed, success, retry, transport assertions |

## Deterministic validation

```text
node --test v2/rp_runtime/tests/player-decomposition-phase.test.mjs v2/rp_runtime/tests/player-visibility-triage-phase.test.mjs
pytest v2/domain/tests/test_issue_124_semantic_normalization.py v2/domain/tests/test_issue_120_generalized_internal.py v2/domain/tests/test_issue_121_uniform_projection.py -q
```

**Result:** 19/19 Node; 28/28 pytest — all pass.

## Updated forensic evidence map

| Stage | Self-contained in PVR/session (execution evidence optional)? |
|-------|--------------------------------------------------------------|
| Player source | Yes — `rp_history` / phase input |
| Inference identity | Yes — `generation.inference_id`, `attempt_index` |
| Raw semantic response (success) | Yes — `generation.raw_semantic_output` |
| Raw semantic response (terminal `sir_malformed`) | **Yes (post-remediation)** — `generation.raw_semantic_output` |
| Parse failure reason | Yes — `failure_class`, `reason` |
| Retry / terminal disposition | Yes — attempt count, `failure_class`, exhausted-retry paths |
| Direct execution-evidence join | **Yes (post-remediation)** — `generation.evidence_id` when recorder enabled |
| Full request/response payloads | Execution evidence only (when `HG_EXECUTION_EVIDENCE` enabled) |
| Normalization audit detail | PVR on success; `generation.normalization` on terminal normalize failure |
| Canonical PVR authority | Session/PVR record — execution evidence is forensic, not perceptual authority |

**Conclusion:** Terminal `sir_malformed` reconstruction no longer depends on execution evidence for raw semantic output.

## Token policy (unchanged)

- ≤2 semantic attempts (`MAX_PLAYER_DECOMPOSITION_ATTEMPTS`)
- `player_decomposition` inference tokens uncapped
- Deterministic normalization search budget 15,000 nodes (`NORMALIZER_VERSION = 3`)

## Greptile re-review

See companion record `issue-124-pr127-greptile-rereview-forensic-hardening-2026-09-05.md`.

**Integration:** NOT authorized. PR #127 remains OPEN and unmerged.
