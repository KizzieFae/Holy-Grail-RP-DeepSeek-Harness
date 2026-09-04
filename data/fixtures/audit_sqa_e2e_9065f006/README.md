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

## Publication policy (this packet only)

This evidence packet follows an **explicit audit publication policy** scoped to this fixture:

1. **Runtime visibility restrictions** (`character_private`, `character_memory`, `authored_role_private`, `orchestration_only`, role-private story knowledge, etc.) enforce **in-story information boundaries** during execution.
2. Those restrictions do **not** by themselves classify fictional RP content as confidential repository material for this audit packet.
3. Selected forensic evidence **intentionally preserves full-fidelity fictional RP content** so reviewers can independently verify information-flow and audit claims.
4. **`response.reasoning_text` remains omitted** from published execution-evidence copies (hidden model reasoning is not required for RP forensic review).
5. **Prohibited in repository publication:** credentials, API keys, authentication/session tokens, secrets granting access to external systems, unrelated real-world PII, and unrelated private user data.

**Greptile GRT-03 disposition:** Greptile correctly observed that orchestration-only / authored-role-private fictional content is visible in published correction evidence. Under this policy, that observation is **not** a repository publication defect.

This policy applies to **this evidence packet only** — it does not create a generalized repository-wide governance authority.

## Why runtime originals remain ignored

Normal session and execution-evidence trees stay gitignored per `docs/rp-data-layout.md`. This PR **deliberately promotes a bounded copy** of selected primary evidence into the already tracked `data/fixtures/` surface. The local runtime originals are unchanged.

## What is included

| Category | Contents |
|----------|----------|
| Canonical session JSON | Full snapshot: `sessions/hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa.json` |
| Player decomposition (SQA-01) | All **36** bounded decomposition attempts |
| Opening segmentation (SQA-02a/02b) | Both failed attempts (`45936195-…`, `f5ec556e-…`) |
| Information-flow turn chains (SQA-03) | Director / Character / Narrator chains for turns 1, 7, 11, 12 |
| Plot/Librarian corrections (SQA-04b) | **Complete population of 20** contract-correction attempts (17 Plot + 3 Librarian) |
| Trimmed execution-evidence index | `execution_evidence/.../index.json` — **70 published attempts** (not 341) |

## What is intentionally excluded

- The complete 341-attempt execution-evidence index and unstaged attempts
- The full Plot Cognition forensic tree (~472 files)
- Story knowledge overlays not required for accepted findings
- Character semantic-rejection attempt files (SQA-06 supported via session JSON metadata)
- Export tooling, generalized audit-evidence policy, or remediation artifacts
- `response.reasoning_text` in published execution-evidence copies

## Sanitization policy

Published execution-evidence copies are **curated forensic evidence**, not byte-identical archival copies. Operations on **copies only** (runtime originals never altered):

1. **`response.reasoning_text` removed** where present.
2. **Fictional RP forensic content preserved** at full fidelity (`character_private`, `character_memory`, `authored_role_private`, `orchestration_only` knowledge, etc.).
3. **Trimmed `index.json`** documents itself as non-complete (see `publication_note`).

Details: `evidence_manifest.json` → `publication`.

The canonical session JSON is included **without transformation**.

## SQA-04b reproducibility (published subset)

Population predicate (`evidence_manifest.json` → `finding_evidence_mapping.SQA-04b.reproducibility`):

```text
correlation.inference_kind in {
  "plot_cognition_update_contract_correction",
  "librarian_proposal_contract_correction"
}
```

| Subpopulation | Count | Token total |
|---------------|-------|-------------|
| Plot (`plot_cognition_update_contract_correction`) | 17 | 183,006 |
| Librarian (`librarian_proposal_contract_correction`) | 3 | 30,329 |
| **Combined** | **20** | **213,335** |

Token derivation: for each attempt, `response.usage.total_tokens` if present, else `inputTokens + outputTokens + (reasoningTokens or 0)`; sum per subpopulation.

## Finding → evidence map

| Finding | Primary artifacts |
|---------|-------------------|
| **SQA-01** | Session PVR records + all 36 `player_decomposition` attempts |
| **SQA-02a** | Opening segmentation attempts + session opening canon |
| **SQA-02b** | Same opening attempts + session continuation after degradation |
| **SQA-03** | Turn 1 / 7 / 11 / 12 execution-evidence chains (see manifest) |
| **SQA-04b** | All 20 contract-correction attempts (17 Plot + 3 Librarian) |
| **SQA-06** | Session JSON (semantic validation / retry metadata) |

**SQA-04a is not a separate finding** — failed decomposition/segmentation token costs are impact evidence for SQA-01 and SQA-02a.

## Investigation tools

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

## Source checksums (original runtime, at export)

| Artifact | SHA-256 |
|----------|---------|
| `data/sessions/hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa.json` | `079931022290eb28dc4646492bc72c30a185d24a7ecf4fdb46510e95d6945104` |
| `data/execution_evidence/.../index.json` (complete) | `dff687535b6caadce2dfd64f5768d1502f880f104b32483fc5f10374b48b5ebf` |
