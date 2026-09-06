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

## Architecture

- **Host authority:** `finalize_prompt_contribution_manifest` (Python) emits canonical manifests for role-turn paths; plot-cognition lifecycle prepare endpoints emit `manifest_id` + `inference_kind` metadata.
- **DSH transport:** `v2/rp_runtime/src/lib/bridge-manifest.mjs` copies only contract fields present on Host prepare responses; callers supply final `contributions`.
- **Bridge validation:** `manifest-validation.mjs` unchanged.

---

## Registered inference kinds (plot-cognition)

| Kind | Allowlist |
|------|-----------|
| `plot_cognition_init` | `active_constraints` |
| `plot_cognition_init_contract_correction` | same as init |
| `plot_cognition_update` | `active_constraints`, `advisory_context` |
| `plot_cognition_update_contract_correction` | same as update |
| `plot_cognition_epistemic_eval` | `active_constraints`, `derived` |
| `plot_cognition_epistemic_eval_contract_correction` | same as epistemic |
| `character_advisory_generation` | `active_constraints`, `derived` |

---

## Files changed

| Area | Files |
|------|-------|
| Adapter | `v2/rp_runtime/src/lib/bridge-manifest.mjs` |
| Policy | `manifest_projection_policy.py`, `manifest-projection-policy.mjs` |
| Envelopes | `character-orientation-envelope.mjs`, `character-semantic-evaluation.mjs`, `semantic-qa-substrate.mjs`, storyteller/librarian envelopes, `plot-cognition-update-envelope.mjs`, `plot-cognition-orchestration.mjs`, `plot-cognition-character-projection.mjs` |
| Tests | `bridge-manifest.test.mjs`, `test_issue_138_manifest_projection_policy.py` |
| Docs | `PACKET_CONTRACTS.md`, this record |

---

## Relationship to #134

Issue #134 established fail-closed model-context validation for role-turn inference paths. Plot-cognition lifecycle (#63) and auxiliary DSH envelope helpers were not fully enrolled. #138 completes the contract without weakening bridge policy.

---

## Validation evidence

**Implementation candidate SHA:** `53c8f68e2c025b2cb492f6f546359cc1916c0963`

| Suite | Result |
|-------|--------|
| `pytest tests/test_issue_138_manifest_projection_policy.py` | pass |
| `pytest tests/test_manifest_policy_parity.py` | pass |
| `pytest tests/test_issue_134_manifest_projection_policy.py` | pass |
| `pytest v2/domain/tests/` (full) | 1050 passed |
| `node --test tests/bridge-manifest.test.mjs` | pass |
| `node --test tests/manifest-validation.test.mjs` | pass |
| `node --test tests/semantic-evaluation-live-pass.test.mjs` | pass |
| `node --test tests/plot-cognition-orchestration.test.mjs` | pass |
| `node --test tests/director-semantic-qa-orchestration.test.mjs` | pass |
| `node --test tests/plot-cognition-character-projection.test.mjs` | pass |
| `node --test tests/librarian-proposal-contract.test.mjs` | pass |

**Runtime advancement:** `two-character-round` primary case advances past prior `plot_cognition_init` / `missing inference_kind` blockers; current failure is `librarian_persistence_failure` (downstream of restored manifest infrastructure).

**Greptile:** SUCCESS on `53c8f68e2c025b2cb492f6f546359cc1916c0963` — 18 files reviewed, 0 comments, confidence 5/5 (check run `101463567879`). Record: `governance/records/issue-138-pr139-greptile-review-2026-09-06.md`. PR head `79610e3` is docs-only after Greptile run.
