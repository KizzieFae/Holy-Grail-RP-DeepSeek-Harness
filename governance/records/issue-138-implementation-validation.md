# Issue #138 — Implementation and Validation Record

**Issue:** [#138 — Preserve and register inference_kind across production manifest paths](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/138)

**Branch:** `issue-138-inference-kind-manifest-contract`

**Assigned workflow weight:** `standard`

**Effective workflow weight:** `full`

**Parent context:** Blocks [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136) scenario-grade validation (infrastructure only; not #136 remediation).

---

## Consensus (Governance-authorized)

Restore #134 manifest contract by:

1. Closed-field DSH `bridgeManifestFromHostPrepare` adapter preserving authoritative Host metadata.
2. Register seven production plot-cognition inference kinds with evidence-derived `source_kind` allowlists (`derived`, `advisory_context` only where production requires).
3. Correction kinds share primary allowlists (same manifest object reused).
4. Exclude `plot_cognition_replan` (no production bridge path).
5. Bridge validation unchanged (fail-closed).

---

## Correction-kind inventory (post-remediation)

Production `runInferenceWithContractCorrection` surface — **four** distinct correction kinds:

| Correction kind | Primary kind | Registry status |
|-----------------|--------------|-----------------|
| `plot_cognition_init_contract_correction` | `plot_cognition_init` | Registered (initial #138) |
| `plot_cognition_update_contract_correction` | `plot_cognition_update` | Registered (initial #138) |
| `plot_cognition_epistemic_eval_contract_correction` | `plot_cognition_epistemic_eval` | Registered (initial #138) |
| `librarian_proposal_contract_correction` | `librarian_proposal` | **Registered (bounded remediation)** |

No other production `src/` correction kinds found.

---

## Architecture

- **Host authority:** `finalize_prompt_contribution_manifest` (Python) emits canonical manifests for role-turn paths; plot-cognition lifecycle prepare endpoints emit `manifest_id` + `inference_kind` metadata.
- **DSH transport:** `v2/rp_runtime/src/lib/bridge-manifest.mjs` copies only contract fields present on Host prepare responses; callers supply final `contributions`.
- **Correction substrate:** When `manifest_id` present, correction attempt reuses manifest with `{ ...manifest, inference_kind: correctionInferenceKind }`; contributions unchanged.
- **Bridge validation:** `manifest-validation.mjs` unchanged (fail-closed).

---

## Registered inference kinds

### Plot-cognition (initial implementation)

| Kind | Allowlist |
|------|-----------|
| `plot_cognition_init` | `active_constraints` |
| `plot_cognition_init_contract_correction` | same as init |
| `plot_cognition_update` | `active_constraints`, `advisory_context` |
| `plot_cognition_update_contract_correction` | same as update |
| `plot_cognition_epistemic_eval` | `active_constraints`, `derived` |
| `plot_cognition_epistemic_eval_contract_correction` | same as epistemic |
| `character_advisory_generation` | `active_constraints`, `derived` |

### Librarian proposal correction (bounded remediation)

| Kind | Allowlist |
|------|-----------|
| `librarian_proposal` | `inference_instruction`, `active_constraints`, `librarian_knowledge` |
| `librarian_proposal_contract_correction` | **identical to primary** (manifest reuse; contributions unchanged on correction) |

---

## Greptile history

| Review | SHA | Result |
|--------|-----|--------|
| Initial implementation | `53c8f68e2c025b2cb492f6f546359cc1916c0963` | SUCCESS 5/5, 0 comments (check `101463567879`) — superseded for final production/test gate |
| Post-remediation | _(record after Greptile completes)_ | Required on exact production/test candidate |

Record: `governance/records/issue-138-pr139-greptile-review-2026-09-06.md` (initial review only).

---

## Validation evidence

**Pre-remediation PR head:** `451a8da8c005a1797d66e8d1d2c409c666b0412e`

**Post-remediation production/test candidate SHA:** `d8a6e5e100e2fd0ba82e30c74079f18a95e98a83`

| Suite | Result |
|-------|--------|
| `pytest tests/test_issue_138_manifest_projection_policy.py` | pass (incl. librarian correction allowlist parity) |
| `pytest tests/test_manifest_policy_parity.py` | pass |
| `pytest tests/test_issue_134_manifest_projection_policy.py` | pass |
| `pytest v2/domain/tests/` (full) | 1051 passed |
| `node --test tests/librarian-proposal-contract.test.mjs` | pass (incl. manifest-backed correction) |
| `node --test tests/librarian-proposal-orchestration.test.mjs` | pass |
| `node --test tests/two-character-round.test.mjs` | **pass** (`no_eligible_actors`; prior `librarian_proposal_contract_correction` blocker cleared) |
| `node --test tests/contract-conformance.test.mjs` | pass (plot-cognition correction kinds intact) |
| `node --test tests/manifest-validation.test.mjs` | pass |
| `node --test tests/bridge-manifest.test.mjs` | pass |
| `node --test tests/semantic-evaluation-live-pass.test.mjs` | pass |
| `node --test tests/plot-cognition-orchestration.test.mjs` | pass |
| `node --test tests/plot-cognition-character-projection.test.mjs` | pass |
| `node --test tests/director-semantic-qa-orchestration.test.mjs` | pass |
| `node --test tests/hg-context-bridge.test.mjs` | pass |
| `npm test` (full rp_runtime gate) | see remediation report — unrelated pre-existing failures observed; suite hung on long-running live test |

**Runtime advancement:** `two-character-round` primary case now completes with `completion_reason: no_eligible_actors` (2 character turns, 2 narrations).

---

## Files changed (cumulative #138)

| Area | Files |
|------|-------|
| Adapter | `v2/rp_runtime/src/lib/bridge-manifest.mjs` |
| Policy | `manifest_projection_policy.py`, `manifest-projection-policy.mjs` |
| Envelopes | character/storyteller/librarian/plot-cognition envelopes, `contract-correction-substrate.mjs` |
| Tests | `bridge-manifest.test.mjs`, `test_issue_138_manifest_projection_policy.py`, `librarian-proposal-contract.test.mjs` |
| Docs | `PACKET_CONTRACTS.md`, this record, Greptile record |

---

## Relationship to #134

Issue #134 established fail-closed model-context validation for role-turn inference paths. #138 completes enrollment for plot-cognition lifecycle paths, DSH envelope preservation, and the production-reachable Librarian proposal correction kind without weakening bridge policy.
