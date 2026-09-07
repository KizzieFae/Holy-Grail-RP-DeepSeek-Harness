# Issue #146 — Storyteller Assessment Contract Investigation + Architecture Proposal

**Date:** 2026-09-07  
**Issue:** [#146](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/146)  
**Phase:** investigation / architecture proposal (implementation **not** authorized)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full  
**Investigation anchor SHA:** `58b1a78` (branch `issue-144-storyteller-orientation-response-contract`)  
**Upstream evidence:** `data/issue144_live_sentinel/2026-09-07T00-29-24-814Z/`  
**Parent context:** [#144](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/144) orientation repair; [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136) Storyteller-bound G2 gate blocked

---

## Activation state

| Field | Value |
|-------|-------|
| Issue state | OPEN |
| Current status | `investigating` |
| Project Status | In Progress |
| Project Workflow | Investigating |
| Priority | P3 |
| Implementation | NOT authorized |
| Merge / closure | NOT authorized |

---

## Root-cause classification

**Type A (primary), with Type C nuance and assessment-specific field-shape divergence.**

Authoritative domain contract exists; Host **structural response-contract projection is absent**; DSH carries schema **name** plus duplicated behavioral prose but **no exemplar or field vocabulary**. Live model reasoning explicitly states schema uncertainty and invents top-level keys (`assessment`, `opportunities`) that do not match canonical section names (`observations`, `progression_opportunities`, etc.).

**Not Type B:** projection is not correct or complete.  
**Not Type D alone:** same architectural defect class as pre-#144 orientation; assessment adds richer canonical shape and wrong invented field names beyond wrapper omission.

---

## Investigation A — Authoritative assessment contract

### Parser / service entry path

```text
runStorytellerCognition (DSH)
  → domainApi.prepareStorytellerAssessmentContext
    → DomainKernel.prepare_storyteller_assessment_context
      → StorytellerService.prepare_assessment_context
        → build_storyteller_assessment_context
  → runEphemeralInference (storyteller_assessment)
  → parseStorytellerAssessment (DSH pre-check; optional pass-through)
  → domainApi.finalizeStorytellerAssessment
    → StorytellerService.finalize_assessment
      → parse_storyteller_assessment (authoritative)
      → build_storyteller_advisory_package (semantic assembly)
```

HTTP: `POST /v1/storyteller/assessment/finalize` → `http_transport.py` → kernel → service.

### Canonical accepted assessment shape (structural parse)

**Root:** JSON object only.

**Structurally required for `parse_storyteller_assessment` acceptance:**

| Requirement | Rule |
|-------------|------|
| `schema` | Must equal exactly `hg_storyteller_assessment_v1` |
| Prohibited keys | None of `PROHIBITED_STORYTELLER_FIELDS` at any depth |

**No additional root keys are structurally required at parse time** (unlike orientation's `information_gaps`).

**Semantically consumed sections** (parsed leniently in `build_storyteller_advisory_package`; empty arrays if absent/malformed):

| Section | Entry shape (when present) |
|---------|---------------------------|
| `observations` | `{text, evidence_refs[], confidence?}` |
| `active_tensions` | `{label, interpretive_note, evidence_refs[], issue_refs?}` |
| `narrative_priorities` | `{focus, why_it_matters, evidence_refs[], confidence?}` |
| `progression_opportunities` | `{opportunity_label, narrative_hook, evidence_refs[], confidence?}` |
| `unresolved_threads` | `{thread_label, neglect_risk, evidence_refs[]}` |
| `uncertainty` | `{topic, reason, confidence?}` |
| `information_gaps` | `{question, blocking_judgment?}` |
| `preservation_signals` | `{subject_label, narrative_significance_note, attention_refs[]}` (rejects if `evidence_refs` present) |
| `evidence_refs` | top-level array of stable refs |

**Optional / defaulted at package build:**

- `assessment_id` — generated if absent
- `confidence` within section items — defaults to `likely` or `speculative` per type
- Empty section arrays — tolerated (package builds with empty tuples)

**Prohibited fields:** `PROHIBITED_STORYTELLER_FIELDS` in `storyteller_contract.py` (shared with orientation).

**Malformed-output classifications:**

| Reason | Trigger |
|--------|---------|
| `parse_error:*` | Invalid JSON string |
| `not_object` | Non-object JSON |
| `schema_mismatch` | Missing/wrong `schema` |
| `prohibited_fields:*` | Prohibited key present |

**Round/KAR validation after structural acceptance:** None at assessment parse. Package validity binds to round via `AssessmentValidity` using authoritative snapshot id from bundle context.

**Assessment acceptance condition:** `parse_storyteller_assessment` returns parsed dict with `error=None`; finalize then builds advisory package and returns `accepted: true, reason: ok`.

**Authority:** `v2/domain_api/storyteller_contract.py` (`parse_storyteller_assessment`, `build_storyteller_advisory_package`).  
**Tests:** `v2/domain/tests/test_storyteller_s3a.py` (`_valid_assessment`), `v2/domain/tests/test_storyteller_finalize_transport.py`.

---

## Investigation B — Structural authority ownership

| Site | Classification | Notes |
|------|----------------|-------|
| `v2/domain_api/storyteller_contract.py` | **Authoritative domain contract** | `STORYTELLER_ASSESSMENT_SCHEMA`, `parse_storyteller_assessment`, package builders, `PROHIBITED_STORYTELLER_FIELDS` |
| `v2/domain_api/storyteller_service.py` | **Host service** | prepare/finalize; prepare metadata includes `schema` (not model-facing contribution) |
| `v2/domain_api/storyteller_assessment_context.py` | **Host prompt projection** | Behavioral instruction only; `STORYTELLER_ASSESSMENT_CONTRACT = "storyteller_assessment_v1"` is provenance label, **not** parser schema id |
| `v2/rp_runtime/src/lib/storyteller-assessment-envelope.mjs` | **DSH prompt + parser mirror** | `buildStorytellerAssessmentPrompt`, `parseStorytellerAssessment`, duplicate schema constant + prohibited set |
| `v2/rp_runtime/src/lib/storyteller-cognition-substrate.mjs` | **DSH orchestration** | Uses DSH assessment prompt (not transport-only); calls DSH pre-check before finalize |
| `v2/domain/tests/test_storyteller_s3a.py` | **Test fixture** | `_valid_assessment()` shows canonical full shape |
| `v2/rp_runtime/tests/storyteller-round-integration.test.mjs` | **Test fixture** | `MOCK_ASSESSMENT` canonical shape |

### `hg_storyteller_assessment_v1` definition

- **Canonical:** `STORYTELLER_ASSESSMENT_SCHEMA` in `storyteller_contract.py` (line 29).
- **Duplicate:** same constant in `storyteller-assessment-envelope.mjs` (line 4).
- **Not canonical:** `storyteller_assessment_v1` in `storyteller_assessment_context.py` (provenance only).

### Host structural projection

**No** Host-owned assessment response-contract contribution exists (contrast orientation post-#144 `storyteller_orientation_response_contract` at priority 28).

### DSH hand-authored schema text

Yes: `buildStorytellerAssessmentPrompt` names schema and duplicates behavioral task; **no structural exemplar or section vocabulary**.

### Sharing with orientation

- **Legitimate shared:** `PROHIBITED_STORYTELLER_FIELDS` in `storyteller_contract.py`.
- **Accidental parallel:** DSH envelope pattern mirrors pre-#144 orientation; orientation post-#144 moved to transport-only user prompt while assessment did not.

---

## Investigation C — Model-facing assessment prompt path

### End-to-end path (preserved live evidence)

```text
orientation accepted (1b2dccef…)
  → prepareStorytellerAssessmentContext (Host)
  → manifestFromStorytellerAssessmentPrepareResponse
  → runEphemeralInference({
       prompt: buildStorytellerAssessmentPrompt(),
       manifest: Host contributions,
       inferenceKind: storyteller_assessment
     })
  → model raw output (965eb382…)
  → parseStorytellerAssessment (fails schema_mismatch)
  → finalizeStorytellerAssessment (raw forwarded; Host rejects schema_mismatch)
```

| Item | Value |
|------|-------|
| inference_kind | `storyteller_assessment` |
| manifest policy | `_COMMON_INSTRUCTION \| {librarian_knowledge}` |
| contribution order | `storyteller_orientation_summary` (10) → `librarian_bundle_digest` (30) → `storyteller_assessment_instruction` (100) |
| Host structural contribution | **Absent** |
| DSH user_instruction | Full behavioral + `Return ONLY one JSON object matching schema hg_storyteller_assessment_v1.` |
| Schema exemplar | **Absent** |
| Section field vocabulary | **Absent** |
| Enum visibility | **Absent** (confidence defaults applied at package build) |
| Duplication | Behavioral task near-duplicated Host contribution ↔ DSH user prompt |

Contrast orientation (same sentinel, accepted): Host `storyteller_orientation_response_contract` (28) + `LIVE_INFERENCE_TRANSPORT_PROMPT` user line only.

---

## Investigation D — Exact failing raw assessment (`965eb382…`)

| Check | Result |
|-------|--------|
| Valid JSON | **Yes** |
| Root object | **Yes** |
| `schema` present | **No** |
| Top-level keys emitted | `assessment` (string), `opportunities` (array) |
| Parser structurally required | `schema` — **missing** |
| Canonical section keys present | **None** (`observations`, `progression_opportunities`, etc. absent) |
| Invented shape | `opportunities[].description` vs canonical `progression_opportunities[].opportunity_label` + `narrative_hook` |
| Semantically plausible content | **Yes** (narrative assessment quality reasonable) |
| Schema-only fix sufficient for parse? | **Yes** — if only `schema` added, parse would pass (invented keys not prohibited) |
| Schema-only fix sufficient for useful package? | **No** — package would be empty across all advisory sections |
| Additional structural mismatch beyond schema | **Yes** — wrong section vocabulary; not equivalent to orientation's wrapper-only gap |

Model reasoning: *"We don't have the schema definition… infer from task… assessment and opportunities."*

---

## Investigation E — DSH assessment parser/pre-check

| Item | Value |
|------|-------|
| Function | `parseStorytellerAssessment` in `storyteller-assessment-envelope.mjs` |
| Accepted shape | Mirrors Host: `schema === hg_storyteller_assessment_v1` + prohibited scan |
| Duplicate constants | Yes (`STORYTELLER_ASSESSMENT_SCHEMA`, prohibited set) |
| On success | Parsed object forwarded to Host finalize |
| On failure | **Raw string forwarded** (`assessmentRun.raw`) — #142-compatible |
| Removal impact | Would not weaken Host; would only remove DSH-side early classification |
| Semantic authority | **Must not** remain sole contract owner post-repair |

Orientation post-#144: `parseStorytellerOrientation` **removed** from transport path; assessment still uses DSH pre-check + semantic DSH prompt.

---

## Investigation F — Retry/correction behavior

| Mechanism | Storyteller assessment |
|-----------|-------------------------|
| Retry on assessment failure | **No** |
| `storyteller_assessment_contract_correction` inference kind | **No** (not in manifest projection policy) |
| Contract-correction substrate | **No** Storyteller assessment paths |
| DSH correction schema | **No** |
| inference_health recovery | `recovery.state: attempted` recorded; **no** follow-up inference in evidence |

Single assessment inference; on finalize failure returns `stage: assessment_finalize` with no retry loop.

---

## Investigation G — Orientation vs assessment comparison

| Dimension | Orientation pre-#144 | Assessment #146 |
|-----------|---------------------|-----------------|
| Canonical structural authority | `storyteller_contract.py` | `storyteller_contract.py` |
| Host structural projection | Absent (pre-#144) | **Absent** |
| Host behavioral instruction | Thin `inference_instruction` | Thin `inference_instruction` |
| DSH semantic/schema prompt | Schema name only + behavioral dup | Schema name only + behavioral dup |
| DSH parser/pre-check | Was present (removed post-#144) | **Present** (`parseStorytellerAssessment`) |
| Required schema marker | `hg_storyteller_orientation_v1` | `hg_storyteller_assessment_v1` |
| Required fields (parse) | `schema` + non-empty `information_gaps` | `schema` only |
| Exemplar | Absent (pre-#144) | **Absent** |
| Correction/retry | None | None |
| Live raw failure | Missing `schema`; correct `information_gaps` | Missing `schema`; invented `assessment`/`opportunities` |
| Host rejection | `schema_mismatch` | `schema_mismatch` |
| Ownership duplication | Host behavioral + DSH schema-name | Same pattern |

---

## Investigation H — Scope/cohesion

Repair remains a **bounded continuation** of the Storyteller response-contract problem (assessment-specific slice). No cross-role framework, no #136 Character work, no #142 transport changes, no #144 orientation edits.

**Adjacent work to keep within #146:**

- Assessment Host structural projection module
- DSH transport-only prompt alignment (mirror #144)
- DSH envelope demotion to test-compat / schema export (mirror orientation post-#144)
- Deterministic + bounded live sentinel extension for orientation→assessment binding

**No new Issue recommended** unless implementation discovers materially independent subsystem defects during build.

---

## Investigation I — Assessment-specific feasibility

| Question | Answer |
|----------|--------|
| Can `storyteller_assessment_context.py` own projection? | **Yes** — add structural contribution via imported assessment response-contract module |
| Must orientation module change? | **No** — #144 isolation preserved |
| Prohibited-field coupling | **Read-only** import from `storyteller_contract.py`; no framework required |
| General Storyteller framework necessary? | **No** — mirror orientation module pattern only |

---

## Architecture alternatives

### Option A — Assessment-specific canonical response-contract module (RECOMMENDED)

`v2/domain/modules/storyteller_assessment_response_contract.py` → Host projection contribution (priority ~28) → DSH `LIVE_INFERENCE_TRANSPORT_PROMPT`.

| Criterion | Assessment |
|-----------|------------|
| Single semantic authority | Strong |
| Host/domain dependency direction | Correct |
| DSH boundary | Aligns with #144 |
| Parser compatibility | No parser weakening |
| Fail-closed preservation | Strong |
| Manifest impact | +1 `inference_instruction` |
| Forensic provenance | revision + digest on contribution |
| #144 isolation | Strong |
| #142 compatibility | Raw forward preserved |
| Scope | Small, bounded |

### Option B — Parser module owns projection helpers

Narrower: add projection to `storyteller_contract.py` only. Works but mixes parse procedure with declarative contract; **weaker provenance clarity** than Option A (Character/orientation precedent favors separate module).

### Option C — Inline Host assessment instruction expansion

Embed exemplar in `storyteller_assessment_instruction` priority-100 block. Simplest diff but **blurs behavioral vs structural**; worse forensic digest targeting.

### Option D — Enhance DSH assessment schema prompt only

Rejected as primary: violates Host/domain semantic authority boundary established by #136/#144; duplicates ownership.

### Option E — Retry/correction solution

Would **mask** initial structural defect without fixing projection; not recommended as primary. Defer `storyteller_assessment_contract_correction` unless live validation still fails after Option A.

### Option F — Shared orientation/assessment abstraction

**Not justified now.** Only shared prohibited constants warrant coupling; separate modules with parallel shape suffice.

---

## Recommended architecture

**Option A** — assessment-specific `storyteller_assessment_response_contract.py` mirroring orientation #144 pattern.

### Proposed ownership boundary

```text
storyteller_assessment_response_contract.py  ← canonical schema, compact exemplar, digest, projection text
storyteller_contract.py                      ← parser/validation (import schema constant; PROHIBITED_* stays)
storyteller_assessment_context.py            ← structural (28) + behavioral (100) contributions
storyteller-assessment-envelope.mjs          ← manifest bridge + test-compat schema export only
storyteller-cognition-substrate.mjs          ← LIVE_INFERENCE_TRANSPORT_PROMPT for assessment
```

### Proposed minimal model-facing projection

- Required: `schema: "hg_storyteller_assessment_v1"`
- Compact exemplar showing **canonical section names** with one minimal item each (not full parser enumeration):
  - `observations`, `progression_opportunities` (minimum viable advisory signal)
  - Optional single-item stubs for other sections **only if token budget allows**; prefer 2–3 representative sections over full schema dump
- Prohibition summary (reference shared prohibited fields)
- Explicit: `evidence_refs` use `{ref_kind, stable_ref}` objects (live model used bare `"entry-1"` strings in opportunities)

### Proposed DSH disposition

- Replace `buildStorytellerAssessmentPrompt` semantic content with `LIVE_INFERENCE_TRANSPORT_PROMPT`
- Retain `STORYTELLER_ASSESSMENT_SCHEMA` export for tests/mocks only
- Demote `parseStorytellerAssessment` to test-compat or remove from hot path (orientation precedent)

### Proposed provenance

- `response_contract_revision`: `storyteller_assessment_response_contract_v1`
- `response_contract_digest`: deterministic SHA-256 over canonical payload (same pattern as orientation)
- No new `source_kind` required (`inference_instruction` sufficient)

### Retry/correction recommendation

**None for initial implementation.** Add correction path only if bounded live validation fails after structural projection.

### Deterministic test strategy

- New `test_issue_146_storyteller_assessment_response_contract.py` (projection text, digest stability, exemplar parse acceptance)
- Extend instruction-ownership test for assessment (no DSH semantic schema prose)
- Existing `test_storyteller_finalize_transport.py` + `test_storyteller_s3a.py` remain regression anchors
- `storyteller-round-integration.test.mjs` mock path unchanged

### Bounded live validation strategy

- Extend `run-issue144-live-sentinel.mjs` (or sibling script) for assessment acceptance + `bound=true` on same provider profile
- Reuse preserved sentinel session fixture; **one** bounded live run after implementation authorized
- Success gate: `assessment_finalize.accepted=true` and round `storyteller.bound=true`

### Explicit exclusions

- #144 orientation production changes
- #142 transport/finalize pass-through semantics
- #136 G2/G3/Tier-2 campaign
- Parser weakening
- Cross-role response-contract framework
- Assessment quality tuning beyond structural adherence

### Unresolved questions

1. Minimum exemplar section set for reliable live adherence (2-section vs fuller stub) — resolve during implementation via deterministic tests + one bounded live run.
2. Whether bare-string `evidence_refs` in live output should be rejected at parse time — **out of scope** unless Governance wants stricter ingress (would be parser change).

### Adjacent work within #146

DSH pre-check demotion and evidence_ref shape clarification in exemplar — **remain in #146**, not separate Issues.

---

## Full-weight consensus recommendation

**Proceed to Governance evaluation (steps 3–5).** Evidence supports Type A architectural alignment with #144; bounded assessment-specific repair; no stop conditions triggered.

---

## Challenge / refinement (2026-09-07)

**Phase:** challenge/refinement complete — agreement pending; implementation **NOT** authorized.

Governance accepted investigation findings and Option A in principle. This section settles exact contract details for agreement.

### Challenge 1 — Canonical structural authority

**Dependency direction (mirrors #144 orientation):**

```text
v2/domain/modules/storyteller_assessment_response_contract.py
        OWNS declarative assessment response structure
              │
              ├──→ v2/domain_api/storyteller_contract.py
              │         imports STORYTELLER_ASSESSMENT_SCHEMA (+ section vocabulary constants)
              │         retains parse_storyteller_assessment + package-builder algorithms
              │
              └──→ v2/domain_api/storyteller_assessment_context.py
                        imports projection helpers + provenance
                        emits structural inference_instruction contribution
```

| Definition | Canonical owner | Consumers | Notes |
|------------|-----------------|-----------|-------|
| `STORYTELLER_ASSESSMENT_SCHEMA` | `storyteller_assessment_response_contract.py` | `storyteller_contract.py` (import), DSH envelope (test-compat export only) | Remove duplicate constant from `storyteller_contract.py` |
| `CANONICAL_SECTION_NAMES` | assessment response contract | projector text, digest | Sorted tuple of allowed top-level section keys |
| `REQUIRED_ROOT_FIELDS` | assessment response contract | projector text, digest | `("schema",)` only |
| `CANONICAL_EXEMPLAR` | assessment response contract | projector, tests | Compact E2 exemplar |
| `PROHIBITION_SUMMARY` | assessment response contract | projector, digest | Compact prose; does not duplicate full `PROHIBITED_STORYTELLER_FIELDS` set |
| `RESPONSE_CONTRACT_REVISION` / digest | assessment response contract | structural contribution provenance | Same pattern as orientation |
| `project_storyteller_assessment_response_contract_text()` | assessment response contract | `storyteller_assessment_context.py` | |
| `PROHIBITED_STORYTELLER_FIELDS` | `storyteller_contract.py` | parser + `validate_storyteller_payload` | **Shared** with orientation; not moved |
| `parse_storyteller_assessment` / `_parse_*` / package build | `storyteller_contract.py` | Host finalize only | Algorithms **not** moved |
| `StorytellerConfidence` etc. | `storyteller_contract.py` dataclasses | package builder defaults | **Not** projected to model (orientation precedent) |
| `STORYTELLER_ASSESSMENT_CONTRACT` (`storyteller_assessment_v1`) | `storyteller_assessment_context.py` | provenance label only | Not parser schema id |

**No duplication** of schema constant, section vocabulary, or exemplar between `domain/modules` and `domain_api`.

### Challenge 2 — Parser-valid vs operationally useful

| Layer | Requirement |
|-------|-------------|
| **Parser-valid (ingress)** | `schema === hg_storyteller_assessment_v1` + no prohibited fields |
| **Operationally useful (binding objective)** | At least one **canonical section item** survives package build with non-empty semantic content |

**Minimum useful model-facing vocabulary** (teach names that correct live failure):

1. **Required root:** `schema`
2. **Represented in exemplar (teach shape):** `observations[]`, `progression_opportunities[]`
3. **Named as allowed-only (no exemplar item):** `active_tensions`, `narrative_priorities`, `unresolved_threads`, `uncertainty`, `information_gaps`, `preservation_signals`, `evidence_refs`

**Not taught / forbidden as top-level keys:** `assessment`, `opportunities` (live inventions — explicitly negated in structural prose).

Parser optional ≠ omit from contract. Semantically consumed ≠ must appear in exemplar.

### Challenge 3 — Exemplar strategy

**Recommended: E2** (compact representative exemplar + canonical section-name line).

| Strategy | Verdict |
|----------|---------|
| E1 | Insufficient — model may not learn other legitimate section names |
| E2 | **Selected** — corrects `assessment`/`opportunities` confusion; names other sections without E3 cost |
| E3 | Rejected — context cost; implies empty-array boilerplate; over-specifies parser |

### Challenge 4 — Exact item shapes (from `_parse_observations`, `_parse_opportunities`)

**`observations[]` item (exemplar):**

```json
{ "text": "<non-empty string>" }
```

- Parser requires: `text` (non-empty after trim)
- Optional at item level: `evidence_refs[]`, `confidence` (default `likely`) — **omitted from exemplar per R3**

**`progression_opportunities[]` item (exemplar):**

```json
{
  "opportunity_label": "<non-empty string>",
  "narrative_hook": "<non-empty string>"
}
```

- Parser requires: both `opportunity_label` and `narrative_hook` (non-empty)
- **Not** `description` (live invention)
- Optional: `evidence_refs[]`, `confidence` — omitted from exemplar per R3

### Challenge 5 — `evidence_refs` disposition

**Decision: R3** — exclude from phase-1 structural projection.

| Question | Answer |
|----------|--------|
| Required for assessment acceptance? | **No** |
| Required for useful binding? | **No** — items can parse without refs |
| Model must emit top-level `evidence_refs`? | **No** |
| Malformed `evidence_refs` behavior? | **Lenient ignore** — `_parse_evidence_refs` drops non-dicts / missing `stable_ref`; no rejection |
| Implicated in live failure? | **No** — failure was schema + wrong section keys |
| Materially improves #146 acceptance? | **No** — behavioral instruction already says "Cite evidence_refs" |

No ingress tightening in #146.

### Challenge 6 — Required vs allowed wording

**Exact compact wording (structural contribution):**

```text
Storyteller assessment response contract (structural JSON only):
Required: schema "hg_storyteller_assessment_v1".
Return one JSON object only. No markdown or commentary.
Do not use top-level keys "assessment" or "opportunities" — use canonical section names below.
Canonical exemplar:
<JSON>
Other allowed sections (include only when applicable; do not emit empty arrays):
active_tensions, narrative_priorities, unresolved_threads, uncertainty, information_gaps, preservation_signals, evidence_refs.
<PROHIBITION_SUMMARY>
```

**Required:** `schema` only.  
**Canonical optional sections:** named line above; exemplar shows two representative sections.  
**Forbidden:** prohibited mandate fields + explicit negation of `assessment`/`opportunities` top-level keys.

### Challenge 7 — Prohibition summary

**Exact line (mirror orientation pattern):**

```text
Do not include mandate fields such as next_actor, dialogue, narration, structured_move, or continuity mutations.
```

Full `PROHIBITED_STORYTELLER_FIELDS` set remains parser enforcement only.

### Challenge 8 — DSH prompt disposition

| Item | Disposition |
|------|-------------|
| Production assessment user prompt | **`LIVE_INFERENCE_TRANSPORT_PROMPT`** exactly |
| `buildStorytellerAssessmentPrompt` | **Remove production use** in `storyteller-cognition-substrate.mjs`; **delete function** or reduce to deprecated re-export of transport prompt for test migration only; no semantic assessment prose |
| `LIVE_STORYTELLER_ASSESSMENT_PROMPT` | Add alias to `LIVE_INFERENCE_TRANSPORT_PROMPT` (mirror orientation) if tests need named export |

No DSH-owned assessment schema semantics in production path.

### Challenge 9 — DSH pre-check disposition

**Decision: P3** — remove from production hot path; always forward `assessmentRun.raw` to Host finalize.

Evidence (#144 precedent + `issue-144-instruction-ownership.test.mjs`):

- Preserves orchestration flow
- Preserves raw evidence artifact
- Preserves #142 fail-closed (`assessment_result` raw string → Host `schema_mismatch`, HTTP 200)
- Eliminates duplicate semantic acceptance
- No new Host call; no transport 400

`parseStorytellerAssessment` retained as **test-compat export** only (mirror post-#144 `storyteller-orientation-envelope.mjs`).

### Challenge 10 — Provenance / digest

**Yes** — structural contribution carries `response_contract_revision` + `response_contract_digest`.

**Deterministic digest inputs:**

```python
{
  "revision": RESPONSE_CONTRACT_REVISION,  # storyteller_assessment_response_contract_v1
  "schema": STORYTELLER_ASSESSMENT_SCHEMA,
  "required_fields": ["schema"],
  "canonical_section_names": sorted(CANONICAL_SECTION_NAMES),
  "exemplar": CANONICAL_EXEMPLAR,
  "prohibition_summary": PROHIBITION_SUMMARY,
}
```

JSON `sort_keys=True`, `separators=(",", ":")`, SHA-256 hex. No runtime/session values. No new `source_kind`.

### Challenge 11 — Contribution separation / order

| Contribution | Priority | source_kind |
|--------------|----------|-------------|
| `storyteller_orientation_summary` | 10 | `inference_instruction` |
| `storyteller_assessment_response_contract` | **28** | `inference_instruction` |
| `librarian_bundle_digest` | 30 | `librarian_knowledge` |
| `storyteller_assessment_instruction` | 100 | `inference_instruction` |

Priority 28 places structural contract **after** orientation summary and **before** librarian digest — model sees vocabulary before bundle data. No collision; no manifest policy change (`inference_instruction` already allowed).

### Challenge 12 — Parser semantics unchanged

**Confirmed.** Implementation limited to:

- Import canonical `STORYTELLER_ASSESSMENT_SCHEMA` from new module
- Optional import of `CANONICAL_SECTION_NAMES` for tests/digest only

**Not in scope:** stricter sections, stricter `evidence_refs`, parser weakening, package-builder redesign, new rejection categories.

### Challenge 13 — Retry/correction deferred

**Confirmed:** no retry, no `storyteller_assessment_contract_correction`, no schema repair, no second attempt. Live failure with contract visibly projected → **STOP → Governance**.

### Challenge 14 — Bounded live success criteria

**Provider profile:** `deepseek-official` / `deepseek-v4-flash` / `reasoning=low`

**Required gates:**

```text
orientation_finalize.accepted = true
assessment_finalize.accepted = true
storyteller.bound = true
```

**Minimum operational-usefulness gate (structural, not quality):**

After finalize, advisory `package` must satisfy **at least one**:

```text
len(package.observations) > 0
OR len(package.progression_opportunities) > 0
```

Deterministic check on Host-returned package dict. Proves canonical vocabulary survived package build, not merely `{"schema": "..."}` ingress.

One live run only. Contract visibly present in evidence contributions. Failure → STOP.

### Challenge 15 — Deterministic validation plan

| # | Coverage | Proposed artifact |
|---|----------|-------------------|
| 1–3 | Single schema authority; parser imports | `test_issue_146_storyteller_assessment_response_contract.py` |
| 4–7 | Exemplar parses; package non-empty; optional omission valid | same |
| 8–10 | Structural + behavioral separation; digest stable | same + prepare context integration test |
| 11–12 | DSH transport-only; no semantic schema | `issue-146-instruction-ownership.test.mjs` |
| 13 | P3 raw forward | same (mirror #144 raw test for assessment) |
| 14–17 | Fail-closed preserved | `test_storyteller_finalize_transport.py` (existing) |
| 18 | #144 orientation untouched | `test_issue_144_*` (existing, no edits) |
| 19–22 | No new kind; no policy churn; no parser rule change; no retry | ownership + contract tests |
| 23 | Assessment-only scope | code review boundary |

**Commands:**

```bash
pytest v2/domain/tests/test_issue_146_storyteller_assessment_response_contract.py -q
pytest v2/domain/tests/test_storyteller_finalize_transport.py -q
pytest v2/domain/tests/test_storyteller_s3a.py -q
pytest v2/domain/tests/test_issue_144_storyteller_orientation_response_contract.py -q
node --test v2/rp_runtime/tests/issue-146-instruction-ownership.test.mjs
node --test v2/rp_runtime/tests/storyteller-round-integration.test.mjs
```

Live (post-implementation authorization only):

```bash
node v2/rp_runtime/scripts/run-issue146-live-sentinel.mjs
```

### Challenge 16 — Scope / cohesion

All bounded work remains in **#146**. No new Issue. R3 `evidence_refs` deferral and sentinel extension are in-scope.

### Exact proposed JSON exemplar

```json
{
  "schema": "hg_storyteller_assessment_v1",
  "observations": [
    {
      "text": "A narratively significant pattern is visible in the bundle."
    }
  ],
  "progression_opportunities": [
    {
      "opportunity_label": "Optional narrative hook",
      "narrative_hook": "An opportunity the scene could develop without mandating action."
    }
  ]
}
```

### Exact production files (implementation phase — listed for agreement only)

| File | Action |
|------|--------|
| `v2/domain/modules/storyteller_assessment_response_contract.py` | **Add** |
| `v2/domain_api/storyteller_contract.py` | Import schema from module; remove local constant |
| `v2/domain_api/storyteller_assessment_context.py` | Add structural contribution @28 |
| `v2/rp_runtime/src/lib/storyteller-cognition-substrate.mjs` | Transport prompt; raw forward (P3) |
| `v2/rp_runtime/src/lib/storyteller-assessment-envelope.mjs` | Demote to bridge + test export |
| `v2/rp_runtime/src/lib/live-inference-prompts.mjs` | Optional assessment transport alias |
| `v2/domain/tests/test_issue_146_storyteller_assessment_response_contract.py` | **Add** |
| `v2/rp_runtime/tests/issue-146-instruction-ownership.test.mjs` | **Add** |
| `v2/rp_runtime/scripts/run-issue146-live-sentinel.mjs` | **Add** (or extend #144 sentinel) |

### Architecture risks

| Risk | Mitigation |
|------|------------|
| Model emits schema-only empty package | Operational-usefulness gate in live sentinel |
| Model still invents `assessment` key | Explicit negation in structural prose |
| DSH test breakage on prompt removal | Instruction-ownership tests + retained schema export |
| Accidental #144 regression | Separate module; no orientation file edits |

### Unresolved questions (post-refinement)

1. **None blocking agreement.** R3 `evidence_refs` in exemplar deferred; may revisit only if bounded live run passes ingress but fails usefulness gate due to bare-string refs (unlikely given wrong-key primary failure).

### Refinement consensus recommendation

**Full-weight agreement (`consensus_reached`) may be declared** once Governance accepts this refinement. Implementation remains **NOT** authorized until explicit post-agreement authorization.

