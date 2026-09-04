# Audit evidence fixture — session `9065f006`

Curated primary-evidence publication supporting the **End-to-End Session Quality & Information-Flow Audit** for session `hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa`.

**Audit report:** [`governance/records/e2e-session-quality-audit-9065f006.md`](../../../governance/records/e2e-session-quality-audit-9065f006.md)  
**Manifest:** [`evidence_manifest.json`](./evidence_manifest.json)  
**Repository audit anchor:** `211e8888edeac58e451cb7ddc9355ab2ec29808c`

## Purpose

This fixture exists so **Greptile** (or a human reviewer) can independently challenge the accepted audit conclusions without un-ignoring ordinary runtime trees (`data/sessions/`, `data/execution_evidence/`, etc.).

Navigation path:

```text
audit finding (report)
    ↓
evidence manifest (evidence_manifest.json)
    ↓
primary fixture artifact (this directory)
    ↓
tracked implementation / architecture contract (docs/, v2/)
```

## Why runtime originals remain ignored

Normal session and execution-evidence trees stay gitignored per `docs/rp-data-layout.md`. This PR **deliberately promotes a bounded copy** of selected primary evidence into the already tracked `data/fixtures/` surface. The local runtime originals are unchanged.

## What is included

| Category | Contents |
|----------|----------|
| Canonical session JSON | Full snapshot: `sessions/hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa.json` |
| Player decomposition (SQA-01) | All **36** bounded decomposition attempts |
| Opening segmentation (SQA-02a/02b) | Both failed attempts (`45936195-…`, `f5ec556e-…`) |
| Information-flow turn chains (SQA-03) | Director / Character / Narrator chains for turns 1, 7, 11, 12 |
| Plot/Librarian corrections (SQA-04b) | **Complete population of 20** `plot_cognition_update_contract_correction` attempts |
| Trimmed execution-evidence index | `execution_evidence/.../index.json` — **70 published attempts** (not 341) |

## What is intentionally excluded

- The complete 341-attempt execution-evidence index and unstaged attempts
- The full Plot Cognition forensic tree (~472 files)
- Story knowledge overlays not required for accepted findings
- Character semantic-rejection attempt files (SQA-06 supported via session JSON metadata)
- Export tooling, generalized audit-evidence policy, or remediation artifacts

## Sanitization and redaction policy

Published execution-evidence copies are **curated forensic evidence**, not byte-identical archival copies. Operations performed on **copies only** (runtime originals never altered):

1. **`response.reasoning_text` removed** where present (hidden chain-of-thought not required for verification).
2. **`character_private` contribution payloads redacted** — lane `source_kind`, contribution IDs, authority/visibility metadata retained.
3. **`character_memory` contribution payloads redacted** — same structural retention; private interpretation/motivation/tactic content omitted.
4. **Other Character-private lane kinds** (`character_secret`, `private_knowledge`, etc.) redacted if present, with lane metadata retained.
5. **Trimmed `index.json`** documents itself as non-complete (see `publication_note`).

Details and counts: `evidence_manifest.json` → `publication`.

The canonical session JSON is included **without transformation** — it is the user-visible RP and PVR primary record.

## SQA-04b reproducibility (published subset)

From `evidence_manifest.json` → `finding_evidence_mapping.SQA-04b.reproducibility`:

- **Population:** every published attempt where `correlation.inference_kind` contains `plot_cognition_update_contract_correction` (20 records).
- **Count:** `len(complete_contract_correction_attempts) == 20`
- **Token total:** for each attempt, `response.usage.total_tokens` if present, else `inputTokens + outputTokens + (reasoningTokens or 0)`; sum = **213,335**.

## Finding → evidence map

See `evidence_manifest.json` → `finding_evidence_mapping` for machine-readable paths.

| Finding | Primary artifacts |
|---------|-------------------|
| **SQA-01** | Session PVR records + all 36 `player_decomposition` attempts |
| **SQA-02a** | Opening segmentation attempts + session opening canon |
| **SQA-02b** | Same opening attempts + session continuation after degradation |
| **SQA-03** | Turn 1 / 7 / 11 / 12 execution-evidence chains (see manifest) |
| **SQA-04b** | All 20 contract-correction attempts (complete population) |
| **SQA-06** | Session JSON (semantic validation / retry metadata) |

**SQA-04a is not a separate finding** — failed decomposition/segmentation token costs are impact evidence for SQA-01 and SQA-02a.

## Investigation tools

Where supported, override data roots to point at this fixture:

```sh
python tools/investigation/trace_turn_forensics.py \
  hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa turn 1 \
  --sessions-root data/fixtures/audit_sqa_e2e_9065f006/sessions \
  --evidence-root data/fixtures/audit_sqa_e2e_9065f006/execution_evidence
```

```sh
python tools/investigation/list_execution_evidence.py \
  hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa \
  --evidence-root data/fixtures/audit_sqa_e2e_9065f006/execution_evidence
```

## Limitations

- Player-PVR and opening mechanical counts remain export-derived from the full runtime source; see manifest `original_mechanical_counts.note`.
- Plot/Librarian contract-correction **count and token total are reproducible** from the published SQA-04b population.
- Published attempt copies omit `reasoning_text` and redact Character-private/memory contribution payloads where not required for verification.
- This packet does not establish a generalized audit-evidence publication standard.

## Source checksums (original runtime, at export)

| Artifact | SHA-256 |
|----------|---------|
| `data/sessions/hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa.json` | `079931022290eb28dc4646492bc72c30a185d24a7ecf4fdb46510e95d6945104` |
| `data/execution_evidence/.../index.json` (complete) | `dff687535b6caadce2dfd64f5768d1502f880f104b32483fc5f10374b48b5ebf` |
