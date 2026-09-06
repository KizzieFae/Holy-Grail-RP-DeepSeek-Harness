# Issue #136 — Implementation and Validation Record

**Issue:** [#136 — System-level LLM inference-contract assessment](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**PR:** [#137](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/137)  
**Branch:** `issue-136-llm-inference-assessment`  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Pre-mutation anchor:** `f317db8234a6c4205f4171fce3fbe1824087cfbd`  
**Phase-1 historical corpus (non-canonical):** [`issue-136-llm-inference-prompt-corpus-evidence.md`](issue-136-llm-inference-prompt-corpus-evidence.md) at `f317db8`

---

## Consensus (Governance-authorized scope)

### Tier 1 — Director / Character instruction ownership deduplication

- Host `inference_instruction` is canonical for `director_turn` and `character_turn`.
- DSH user prompt is transport-only: `Return only the requested JSON object. No markdown or commentary.`
- No architectural terms (`manifest`, `inference_instruction`) in model-facing DSH text.
- Director domain/selection guidance in `director_scratch`; schema contract in `inference_instruction`.

### Tier 2 — Character state→decision invariant (only new semantic content)

> Ground this turn's beats and motivation in the authoritative Character and scene context already supplied; action, inaction, and change should follow from that context.

### Explicit no-change

Narrator, Storyteller, Librarian, Character context ordering, cognition chain, PVR (#112), narrator env cognition (#131), semantic QA rubrics, plot cognition, card expansion — unchanged.

---

## Files changed

| File | Change |
|------|--------|
| `v2/rp_runtime/src/lib/live-inference-prompts.mjs` | DSH transport-only constants |
| `v2/domain_api/director_context.py` | Expanded `inference_instruction`; expanded `director_scratch` |
| `v2/domain_api/character_context.py` | Expanded `inference_instruction` + Tier 2 invariant |
| `v2/rp_runtime/src/plugins/hg-phase-executors/director-phase.mjs` | Transport fallback prompt |
| `v2/rp_runtime/src/plugins/hg-phase-executors/character-phase.mjs` | Transport fallback prompt |
| `v2/rp_runtime/src/plugins/hg-phase-executors/character-inference-slice.mjs` | Transport default prompt |
| `v2/rp_runtime/scripts/export-live-inference-prompts.mjs` | Test/export helper |
| `v2/domain/tests/test_issue_136_inference_instruction_ownership.py` | Ownership assertions |
| `v2/rp_runtime/tests/issue-136-instruction-ownership.test.mjs` | DSH transport assertions |
| `MODULE_INDEX.md` | Canonical ownership routing |
| `governance/records/issue-136-implementation-validation.md` | This record |

---

## Effective contracts — BEFORE (pre-implementation at `f317db8`)

### Director DSH (`live-inference-prompts.mjs`)

```
Respond with ONLY one JSON object. No markdown, no commentary. Required keys: next_actor (string), end_round (boolean), reason (string), environment_event (string), tension_shift (string). Set tension_shift to exactly escalate, soften, or steady. environment_event is optional; use an empty string instead of repeating a recent accepted environment development. Select next_actor from the eligible cast in context. Set end_round false unless the scene should stop.
```

### Director Host `inference_instruction`

```
Output only JSON with next_actor, end_round, reason, environment_event, tension_shift. tension_shift must be escalate, soften, or steady. environment_event is optional; use an empty string rather than repeating a recent accepted environment development.
```

### Character DSH (`live-inference-prompts.mjs`)

Full inline JSON example + schema keys (`move_schema_version`, `beats`, `motivation`, `semantic_evaluation`, `action`/`dialogue`, `risk_level`).

### Character Host `inference_instruction`

```
Output only valid JSON for move_schema_version 2 with non-empty beats[], motivation object, and semantic_evaluation. Each beat must be type action (key action) or type speech (key dialogue). Action-only, speech-only, and mixed beat sequences are all valid when appropriate to the scene.
```

---

## Effective contracts — AFTER (implementation)

### Director DSH (transport only)

```
Return only the requested JSON object. No markdown or commentary.
```

### Director Host `inference_instruction`

```
Output only JSON with required keys: next_actor (string), end_round (boolean), reason (string), environment_event (string), tension_shift (string). tension_shift must be exactly escalate, soften, or steady. environment_event is optional; use an empty string rather than repeating a recent accepted environment development. Select next_actor from the eligible cast in context. Set end_round to false unless the scene should stop.
```

### Director Host `director_scratch`

```
Director scratch: weigh participation balance when selecting the next actor. Select next_actor from the eligible cast supplied in context. Set end_round to false unless the scene should stop. Do not assume character-private knowledge.
```

### Character DSH (transport only)

```
Return only the requested JSON object. No markdown or commentary.
```

### Character Host `inference_instruction`

```
Output only valid JSON for move_schema_version 2 with non-empty beats[], motivation object, and semantic_evaluation. Each beat must be type action (key action) or type speech (key dialogue). Action-only, speech-only, and mixed beat sequences are all valid when appropriate to the scene. motivation must include goal, tactic, emotional_driver, and risk_level. risk_level must be exactly low, medium, or high. semantic_evaluation must include a decision field. Ground this turn's beats and motivation in the authoritative Character and scene context already supplied; action, inaction, and change should follow from that context.
```

---

## Duplicate content removed

| Lane | Removed from DSH |
|------|------------------|
| Director | `next_actor`, `end_round`, `tension_shift`, `environment_event` schema/domain prose |
| Character | `move_schema_version`, `beats`, inline JSON example, `risk_level`, action/dialogue key rules |

---

## Deterministic validation

| Suite | Result |
|-------|--------|
| `pytest v2/domain/tests/test_issue_136_inference_instruction_ownership.py` | 4 passed |
| `pytest v2/domain/tests/` (full) | 1048 passed |
| `pytest` manifest/director/character regressions (issue 54, 134, director digests, move ingress, semantic QA) | passed |
| `node --test tests/issue-136-instruction-ownership.test.mjs` | passed |
| `node --test tests/semantic-evaluation-orchestration.test.mjs` | passed |
| `node --test tests/director-semantic-qa-orchestration.test.mjs` | passed |
| Character phase orchestration subset | passed |

### Runtime regressions (pre-existing blockers unrelated to #136 prompt diff)

| Test | Failure | Assessment |
|------|---------|------------|
| `execution-evidence-forensic.test.mjs` (participation path) | `unknown inference_kind 'plot_cognition_init'` | Manifest policy parity gap on branch; not introduced by #136 |
| `two-character-round.test.mjs` (primary round) | same | same |
| `semantic-evaluation-live-pass.test.mjs` | `PromptContributionManifest missing required inference_kind` (character knowledge cognition) | same class of runtime/manifest wiring; not #136 prompt ownership |

---

## Scenario-grade validation

### Pre-#138 blocked validation (historical — preserved)

**Status at `f385219`:** **INCOMPLETE** — blocked from primary live round harness by pre-existing manifest/inference-kind infrastructure defects (later governed under Issue #138). Tier 2 multi-turn paired pre/post characterization runs were **not** executed.

| Test (pre-#138) | Failure | Assessment |
|-----------------|---------|------------|
| `execution-evidence-forensic.test.mjs` (participation path) | `unknown inference_kind 'plot_cognition_init'` | #138 infrastructure; not #136 |
| `two-character-round.test.mjs` (primary round) | same | same |
| `semantic-evaluation-live-pass.test.mjs` | missing `inference_kind` on character cognition manifest | same |

**Do not rewrite history:** scenario validation did not succeed before #138.

### Post-#138 activation (2026-09-06)

| Field | Value |
|-------|-------|
| **`main` anchor (#138 integrated)** | `9baf987cc3b29146e863447427b87379af94e4e0` |
| **Validation branch head** | `c16e31e55ba4baf33f8fbbe7611431405827b0e0` |
| **#136 implementation SHA** | `f3852196395505b8077ab817a736c7e7eddef099` (unchanged; merge is mechanical base sync only) |

#### Production-like path readiness (post-#138)

| Stage | Evidence | Result |
|-------|----------|--------|
| Plot cognition init | `two-character-round.test.mjs`, `participation-round.test.mjs` | **PASS** |
| Character orientation / generation / semantic eval | `semantic-evaluation-live-pass.test.mjs` (live provider) | **PASS** |
| Character commit + Narrator | `two-character-round.test.mjs` | **PASS** |
| Storyteller on production `runRound` path | `storyteller-round-integration.test.mjs` | **PASS** (`hg/storyteller-started` → `hg/storyteller-completed`) |
| Forensic evidence chains | `execution-evidence-forensic.test.mjs` | **PASS** (5/5) |

**Conclusion:** #138 removes prior infrastructure blockers. Integrated path operational on `c16e31e`.

#### Deterministic regression (post-#138)

| Suite | Result |
|-------|--------|
| `pytest v2/domain/tests/test_issue_136_inference_instruction_ownership.py` | **4 passed** |
| `pytest v2/domain/tests/` (full) | **1055 passed** |
| `node --test` #136 ownership + orchestration + round + forensic + storyteller integration | **all passed** (see command log in activation report) |
| `node --test tests/semantic-evaluation-scenarios.test.mjs` | **7/7 passed** |

#### Baseline debt (#140 / #141)

| Test | Result | Owner |
|------|--------|-------|
| `reasoning-scaffolding-live.test.mjs` | **FAIL** — missing `inference_kind` | #140 |

#### Scenario-grade semantic campaign (Tier 2 fidelity dimensions)

**Status:** **INCOMPLETE** — path unblocked, but governed multi-fixture forensic campaign across all nine #136 semantic dimensions was **not executed** in this cycle. Bounded live pass (`semantic-evaluation-live-pass`) is insufficient alone for `validated`.

**Governance disposition:** Remain **`implemented`**.

---

## Forensic evidence

- DSH transport prompt: `v2/rp_runtime/src/lib/live-inference-prompts.mjs`
- Host canonical instruction: `v2/domain_api/director_context.py`, `v2/domain_api/character_context.py`
- `character_inference_slice` uses `LIVE_INFERENCE_TRANSPORT_PROMPT` via shared import; Host `prepareCharacterContext` path unchanged

---

## Greptile

| Review | SHA | Scope | Result |
|--------|-----|-------|--------|
| Phase 1 assessment | `b1d10ba` | Assessment docs only | SUCCESS (2 P1 remediated in docs) |
| **Implementation (#136 prod/test)** | `f385219` / post-sync `c16e31e` | Production prompt/ownership diff | **NOT REVIEWED** |

**Required before `validated`:** Greptile review on exact production/test candidate after any base sync. Post-#138 merge commit `c16e31e` adds no #136 production diff; Greptile must still cover implementation files on current PR head.

---

## Workflow state

**Current:** **`implemented`** (not `validated`).

**Blockers to `validated`:** (1) Tier-2 scenario-grade semantic campaign incomplete; (2) Greptile not completed on implementation candidate.

---

## Response-contract implementation cycle (2026-09-06)

**Authorization:** Implementation + deterministic validation + Greptile + bounded Character-only live slice. **Not** authorized: full Tier-2 rerun, `validated`, merge, closure.

### Canonical contract

| Field | Value |
|-------|-------|
| Module | `v2/domain/modules/character_move_response_contract.py` |
| Revision | `character_move_response_contract_v1` |
| Digest | `e5192fb332e8726f4a8c107b2869a32e76b2b93e314964111ffab7eda0f05651` |
| Implementation SHA (feat) | `89876413b11ff2c6f7140fa5aa9a34056f328f8f` |
| PR head (exact candidate) | `bebdd31` (includes harness anchor + live-slice wiring) |

### Architecture delivered

- Declarative contract module owns structural allowlists, exemplar, prohibitions, projection text, provenance digest.
- `character_move_ingress.py` imports structural constants (bounded extraction; validation algorithm unchanged).
- `character_context.py` emits **two** `inference_instruction` contributions: `-response-contract` (priority 28) + `-instruction` (priority 30) with revision/digest on structural contribution only.
- DSH remains transport-only (`LIVE_INFERENCE_TRANSPORT_PROMPT`).
- Correction path reuses identical structural projection (digest parity tested).
- Campaign stop-state machine: `issue136-campaign-state.mjs` + Tier-2 runner integration.

### Files added/changed (this cycle)

| File | Role |
|------|------|
| `v2/domain/modules/character_move_response_contract.py` | Canonical structural authority |
| `v2/domain/modules/character_move_ingress.py` | Import contract constants |
| `v2/domain_api/character_context.py` | Dual Host projections + provenance |
| `v2/domain/tests/test_issue_136_character_move_response_contract.py` | Contract↔ingress + manifest parity |
| `v2/domain/tests/test_issue_136_inference_instruction_ownership.py` | Updated split-contribution assertions |
| `v2/rp_runtime/src/scenario-harness/issue136-campaign-state.mjs` | Stop-state machine |
| `v2/rp_runtime/src/scenario-harness/issue136-tier2-campaign.mjs` | Runner integration |
| `v2/rp_runtime/src/scenario-harness/issue136-character-live-slice.mjs` | Bounded live validation harness |
| `v2/rp_runtime/tests/issue136-campaign-state.test.mjs` | Stop-state unit tests |

### Deterministic validation

| Command | Result |
|---------|--------|
| `pytest v2/domain/tests/` | **1076 passed** |
| `pytest domain/tests/test_issue_136_character_move_response_contract.py domain/tests/test_issue_136_inference_instruction_ownership.py` | **11 passed** |
| `node --test tests/issue136-campaign-state.test.mjs tests/issue-136-instruction-ownership.test.mjs tests/issue136-tier2-campaign-smoke.test.mjs` | **14 passed** |

### Bounded Character-only live slice (not Tier-2)

| Field | Value |
|-------|-------|
| Fixture | `136-T2-A-STABILITY` / character `Mara` |
| Provider / model / reasoning | `deepseek-official` / `deepseek-v4-flash` / `low` |
| Candidate SHA | `89876413b11ff2c6f7140fa5aa9a34056f328f8f` |
| Contract revision / digest | `character_move_response_contract_v1` / `e5192fb3…0f05651` |
| Ingress-accepted move | **Yes** — attempt 0 accepted + committed (`domain_commit_id` `hg-commit-a7610abd-…`) |
| Beat shapes | `type`+`action`, `type`+`dialogue` (no `description`/`key`) |
| `move_schema_version` | Present (`2`) on accepted output |
| Report | `data/issue136_character_live_slice/2026-09-06T23-37-35-335Z/character-live-slice-report.json` |

**Note:** Earlier slice runs failed commit only because harness passed stringified `directorDecision`; fixed in `f679dc4`. Structural ingress succeeded on all attempts even before that fix.

### Storyteller infrastructure sentinel

**Not rerun live** — #142 merged to `main` at `51e1b74` with dedicated validation. Mock Tier-2 harness smoke still completes post stop-state repair.

### Greptile (response-contract cycle)

| Field | Value |
|-------|-------|
| Requested head | `bebdd31` |
| PR | #137 |
| Status at handoff | **Requested** via PR comment; check run not yet reported |

### Remaining obligations

1. Greptile clean review on exact PR head (`bebdd31`+).
2. Full Tier-2 semantic campaign (nine dimensions) — still **unauthorized** until Governance re-authorizes after structural + Greptile gates.
3. Do **not** merge PR #137 or transition #136 to `validated` without Governance authorization.
