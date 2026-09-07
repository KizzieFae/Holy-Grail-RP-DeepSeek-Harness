# Issue #144 — Storyteller Orientation Contract Investigation + Architecture Proposal

**Date:** 2026-09-06  
**Issue:** [#144](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/144)  
**Phase:** investigation / consensus refinement (implementation **not** authorized)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full  
**Investigation anchor SHA:** `a5afeb0000d6e3d999e9ac389f7a715d4038bfa0` (branch `issue-136-llm-inference-assessment`)  
**Upstream evidence SHA (G2/G3 gates):** `b8c4ed57b24486125c62edc4c2f1fd8ae37409a5`  
**Parent blocker context:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136) Storyteller-bound G2 gate

---

## Activation state

| Field | Value |
|-------|-------|
| Issue state | OPEN |
| Current status | `investigating` |
| Project Status (typical) | In Progress |
| Project Workflow (typical) | Investigating |
| Priority | P3 (per intake) |
| Implementation | NOT authorized |
| Merge / closure | NOT authorized |

---

## #136 blocker relationship

#144 was filed because #136 Full-weight Storyteller-bound G2 cannot pass while orientation finalize returns `schema_mismatch` → `bound=false`.

| #136 item | Status |
|-----------|--------|
| Character response-contract repair | Implemented and structurally passing |
| #142 transport repair | Resolved |
| G2 infrastructure sentinel | PASS (structured rejection; no HTTP 400) |
| G2 Storyteller-bound gate | NOT SATISFIED |
| G3 `136-T2-A-STABILITY` ×1 Character path | Accepted + committed |
| G3 Storyteller | Same `schema_mismatch` degradation |
| Full Tier-2 campaign | NOT authorized until Storyteller-bound G2 passes |

Evidence: `governance/records/issue-136-g2-g3-gate-report-2026-09-06.md`, `data/issue136_g2_g3_gates/2026-09-06T23-57-23-541Z/`

---

## Investigation A — Authoritative acceptance contract

### Parser / service entry path

```text
runStorytellerCognition (DSH)
  → domainApi.finalizeStorytellerOrientation
    → DomainKernel.finalize_storyteller_orientation
      → StorytellerService.finalize_orientation
        → parse_storyteller_orientation (authoritative)
```

HTTP: `POST /v1/storyteller/orientation/finalize` → `http_transport.py` → kernel → service.

### Canonical accepted orientation shape

**Root:** JSON object only.

**Required for acceptance:**

| Requirement | Rule |
|-------------|------|
| `schema` | Must equal exactly `hg_storyteller_orientation_v1` |
| `information_gaps` | Non-empty array; each element non-empty string after trim |

**Optional fields (parsed when present):**

- `orientation_id` (generated if absent)
- `hg_round_id`, `turn_index`
- `trigger` ∈ `{round_start, material_commit_refresh, follow_up_gap}` (invalid → default `round_start`)
- `entity_attention` (array of `{ref_kind, stable_ref, display_hint?}`)
- `relationship_focus` (array of `{subject_ref, object_ref?, relationship_kind?}`)
- `temporal_focus` ∈ `{current, recent, historical, session, arc}` (invalid → `current`)
- `breadth_preference` ∈ `{broad, focused}` (invalid → `broad`)
- `requested_classes` (string array)
- `narrative_hypothesis`, `degradation`

**Prohibited root/nested keys:** `next_actor`, `dialogue`, `narration`, `structured_move`, `character_state`, `continuity_mutation`, `plot_beat`, `must_act`, `must_say`, `must_do`, and related mandate fields (`PROHIBITED_STORYTELLER_FIELDS`).

**Additional-property behavior:** Not enforced at parse time beyond prohibited-field scan; unknown keys are tolerated if schema and gaps pass.

### Malformed-output classifications

| Reason | Trigger |
|--------|---------|
| `parse_error:*` | Invalid JSON string |
| `not_object` | Non-object JSON |
| `schema_mismatch` | Missing/wrong `schema` |
| `prohibited_fields:*` | Prohibited key present |
| `information_gaps_required` | Missing/empty `information_gaps` |
| `round_mismatch` | `hg_round_id` present and ≠ bound round (finalize only) |
| KAR validation errors | Post-parse `validate_knowledge_access_request` failure |

**Parsing vs semantic validation:** Structural parse in `parse_storyteller_orientation`; round binding and KAR construction are finalize semantic steps.

### Caps / deterministic restrictions

- No max gap count at parse time.
- KAR budget defaults: `max_bundle_entries=32`, `max_bundle_chars=24000` (downstream, post-accept).

**Authority:** `v2/domain_api/storyteller_contract.py` (`parse_storyteller_orientation`, lines 279–346).  
**Tests:** `v2/domain/tests/test_storyteller_s3a.py`, `v2/domain/tests/test_storyteller_finalize_transport.py`.

---

## Investigation B — Contract ownership

| Site | Classification | Notes |
|------|----------------|-------|
| `v2/domain_api/storyteller_contract.py` | **Authoritative domain contract** | `STORYTELLER_ORIENTATION_SCHEMA`, parser, dataclass, KAR mapping |
| `v2/domain_api/storyteller_service.py` | **Host service** | prepare/finalize orchestration; prepare payload includes `schema` metadata (not model-facing contribution) |
| `v2/domain_api/storyteller_orientation_context.py` | **Host prompt projection** | Behavioral task only; `STORYTELLER_ORIENTATION_CONTRACT = "storyteller_orientation_v1"` is provenance label, **not** parser schema id |
| `v2/rp_runtime/src/lib/storyteller-orientation-envelope.mjs` | **DSH prompt + transport parser mirror** | `buildStorytellerOrientationPrompt`, duplicate `parseStorytellerOrientation` |
| `v2/rp_runtime/src/lib/storyteller-cognition-substrate.mjs` | **DSH orchestration** | Calls DSH prompt builder, not Host contract projector |
| `v2/domain/tests/test_storyteller_s3a.py` | **Test fixture** | `_valid_orientation()` shows required wrapper |
| `governance/records/issue-136-llm-inference-prompt-corpus-evidence.md` §S.1 | **Documentation snapshot** | Historical corpus |
| `v2/domain/modules/storyteller_orientation_ingress.py` | **Does not exist** | Issue body anchor is aspirational; ingress is `parse_storyteller_orientation` in contract module |

### `hg_storyteller_orientation_v1` definition

- **Canonical:** `STORYTELLER_ORIENTATION_SCHEMA` in `storyteller_contract.py` (line 23).
- **Duplicate:** same constant in `storyteller-orientation-envelope.mjs` (line 4).
- **Not canonical:** `storyteller_orientation_v1` in `storyteller_orientation_context.py` (different string; projection provenance only).

### Host response-contract renderer

**No** Host-owned response-contract projection exists for Storyteller orientation (unlike Character `character_move_response_contract.py` + dual `inference_instruction` contributions).

### DSH hand-authored schema text

Yes: `buildStorytellerOrientationPrompt` ends with `Return ONLY one JSON object matching schema hg_storyteller_orientation_v1.` — schema **named** but **no structural exemplar**.

### Disagreement / duplication

- Behavioral instructions duplicated between Host contribution and DSH user prompt (near-verbatim).
- Schema identifier appears only in DSH user line; absent from Host `inference_instruction`.
- Two parsers (Host authoritative; DSH mirror for pre-finalize check).

---

## Investigation C — Live model-facing prompt path

### End-to-end path

```text
hg-round-orchestrator / runStorytellerCognition
  → prepareStorytellerOrientationContext (Host HTTP)
  → manifestFromStorytellerPrepareResponse (DSH bridge)
  → runEphemeralInference({
       prompt: buildStorytellerOrientationPrompt(),
       manifest: Host contributions,
       inferenceKind: storyteller_orientation
     })
  → model output (raw)
  → finalizeStorytellerOrientation (Host) — authoritative accept/reject
```

### G2 assembled prompt (evidence `d11eb44a-536a-49cc-82f6-8508aba0e4cb`)

| Item | Value |
|------|-------|
| inference_kind | `storyteller_orientation` |
| manifest_id | `manifest-storyteller-orient-inf-storyteller-hg-round-23d01d78-…` |
| contribution order | `:storyteller_scene_snapshot` (priority 20) → `:storyteller_orientation_instruction` (priority 100) |
| manifest policy | `DIRECTOR_DIGESTS \| COMMON_INSTRUCTION \| {scene_pressures, scene_state}` per `manifest_projection_policy.py` |

**Host `inference_instruction` (priority 100):**

```text
STORYTELLER ORIENTATION TASK:
Identify what information you need to understand the current narrative situation.
Return focus questions in information_gaps. Do NOT prescribe plot outcomes, actor selection, dialogue, narration, or continuity mutations.
Do NOT reference retrieval backends, candidate ids, or relevance ranks.
```

**DSH user_instruction (transport semantic layer — not transport-only):**

```text
You are the Holy Grail Storyteller orientation phase.
Identify what information you need to understand the current narrative situation.
Populate information_gaps with focus questions for the Librarian.
Do NOT prescribe plot outcomes, actor selection, dialogue, narration, or continuity mutations.
Do NOT reference retrieval backends, candidate ids, or relevance ranks.
Return ONLY one JSON object matching schema hg_storyteller_orientation_v1.
```

| Check | Result |
|-------|--------|
| Contract/schema prose present | Schema **name** only (DSH last line) |
| Required schema wrapper explicit | **No** exemplar showing `"schema": "hg_storyteller_orientation_v1"` |
| Exemplar | **Absent** |
| Enum values explicit | **Absent** (defaults applied at parse) |
| Contradictory structure | Behavioral duplication Host↔DSH; schema salience only in DSH user line |

Model reasoning (G2) explicitly states uncertainty: *"We don't know exact schema… description only mentions information_gaps… I'll produce JSON with information_gaps only."*

---

## Investigation D — Raw failure characterization

### G2 (`d11eb44a-536a-49cc-82f6-8508aba0e4cb`)

| Check | Result |
|-------|--------|
| Valid JSON | **Yes** |
| JSON object | **Yes** |
| `schema` present | **No** |
| `information_gaps` present | **Yes** (10 plausible focus questions) |
| Field names otherwise match domain shape | **Partial** — only `information_gaps`; optional fields omitted (allowed) |
| Semantically plausible | **Yes** |
| Finalize reason | `schema_mismatch` |

Minimal excerpt:

```json
{
  "information_gaps": [
    "What is the current setting (location, time period, environment) where Mara and Jon are present?",
    "..."
  ]
}
```

### G3 (`4abdb42b-be9b-463c-a580-afb91f2402ea` per gate report)

| Check | Result |
|-------|--------|
| Raw attempt artifact in repo tree | **Not preserved** (gate report + forensic summary only) |
| Stage / reason | `orientation_finalize` / `schema_mismatch` (identical to G2) |
| Provider / model / reasoning | Same as G2 |

**Failure identity:** Structurally **presumed identical** (same failure class, same prompt path, same provider config). G3 raw body not independently quotable from preserved artifacts.

---

## Investigation E — Correction / retry behavior

| Mechanism | Storyteller orientation |
|-----------|-------------------------|
| Retry on orientation failure | **No** |
| `storyteller_orientation_contract_correction` inference kind | **No** (not in manifest projection policy) |
| Contract-correction substrate | **No** Storyteller paths |
| DSH correction-only schema | **No** |
| Host reconstruction on retry | N/A |

`runStorytellerCognition` performs a single orientation inference; on finalize failure returns `stage: orientation_finalize` with no retry loop.

---

## Investigation F — Character vs Storyteller comparison

| Dimension | Character pre-#136 | Storyteller orientation #144 |
|-----------|-------------------|------------------------------|
| Canonical domain contract | `character_move_ingress.py` + move schema rules | `storyteller_contract.py` `parse_storyteller_orientation` |
| Model-facing Host projection | Thin `inference_instruction` only | Thin behavioral `inference_instruction` only |
| DSH semantic schema text | Full inline schema + exemplar | Schema **name** in user prompt only; no exemplar |
| Exemplar | Was in DSH (pre-#136) | **Absent** everywhere |
| Required schema/version marker | `move_schema_version: 2` (now in Host contract) | `schema: hg_storyteller_orientation_v1` (parser enforced; not structurally projected Host-side) |
| Correction parity | Character correction reuses contract (post-#136) | **No** correction path |
| Live failure mode | Structural beat/key omissions | **Schema wrapper omission** despite plausible `information_gaps` |
| Ownership duplication | Host+DSH duplicated schema (pre-#136) | Host behavioral + DSH behavioral+schema-name duplication |

### Root-cause classification: **Type A** (primary), with **Type C** nuance

**Type A:** Authoritative domain contract exists; model-facing **Host response-contract projection is absent**; DSH carries insufficient structural salience (name without exemplar/minimal contract block).

**Type C nuance:** DSH does name the schema, and the model still omitted the wrapper — provider adherence is **also** implicated. However, model reasoning shows **ambiguity-driven omission**, consistent with missing structural projection rather than random non-compliance.

**Not Type B:** Projection is not correct and complete.  
**Not Type D:** Same architectural defect class as Character pre-#136 (orientation-specific variant).

---

## Architectural alternatives

### Option A — Host canonical Storyteller orientation response-contract projection (RECOMMENDED)

Add `v2/domain/modules/storyteller_orientation_response_contract.py` (or extend `storyteller_contract.py` with projection helpers only — prefer separate module mirroring Character pattern).

- Declarative: schema id, required root keys, minimal exemplar, prohibitions, enum literals where binding.
- Host `storyteller_orientation_context.py` emits **`-response-contract`** contribution (priority ~28) separate from behavioral instruction (priority 100).
- DSH `buildStorytellerOrientationPrompt` → `LIVE_INFERENCE_TRANSPORT_PROMPT` only.
- Digest/provenance on structural contribution.

| Criterion | Assessment |
|-----------|------------|
| Semantic authority | Strong — single Host module |
| Deterministic ownership | Strong |
| Host/DSH boundary | Aligns with #136 principle |
| Parser compatibility | No parser change required |
| Manifest impact | +1 `inference_instruction` contribution |
| Forensic visibility | Digest on structural contribution |
| Correction parity | Enables future correction reuse |
| Testability | High (contract↔parser parity tests) |
| Scope | Small, orientation-specific |
| Risk of duplication | Low if DSH deduped |
| Prompt verbosity | Low with compact exemplar |
| Fail-closed | Preserved |
| Storyteller-specific | Yes |

### Option B — Repair existing Host projection only

Expand `storyteller_orientation_instruction` to include schema wrapper + exemplar inline.

| Criterion | Assessment |
|-----------|------------|
| Semantic authority | Moderate — no digest/revision |
| Scope | Smallest diff |
| Risk | Duplication with DSH until DSH stripped; no provenance digest |
| Recommendation | Acceptable fallback; weaker than Option A |

### Option C — Restore/enhance DSH schema instruction

Keep/enlarge DSH `buildStorytellerOrientationPrompt` with full schema dump.

| Criterion | Assessment |
|-----------|------------|
| Host/DSH boundary | **Violates** #136 ownership principle |
| Duplication risk | High |
| Recommendation | **Reject** as primary fix |

### Option D — Retry/correction-only

Add orientation retry with correction prompt carrying schema.

| Criterion | Assessment |
|-----------|------------|
| Root cause | Does not fix attempt-0 contract gap |
| Cost | Extra live inference |
| Recommendation | **Defer**; optional supplement after Option A |

### Option E — Generalized cross-role framework

Shared abstraction across Character/Storyteller/Director.

| Criterion | Assessment |
|-----------|------------|
| #136 precedent | User rejected premature generalization |
| Evidence | Single-role defect; assessment is follow-on only |
| Recommendation | **Defer** |

---

## Recommended architecture

**Option A** with DSH deduplication to transport-only (mirror #136 Character repair).

### Proposed ownership boundary

```text
storyteller_contract.py (parse + dataclass + schema constant)  ← authoritative acceptance
storyteller_orientation_response_contract.py                     ← declarative structural projection
storyteller_orientation_context.py                             ← behavioral instruction + contract contribution
storyteller-orientation-envelope.mjs                           ← transport prompt only; parser mirror retained for DSH pre-check
storyteller-cognition-substrate.mjs                            ← uses LIVE_INFERENCE_TRANSPORT_PROMPT
```

### Proposed projection shape (compact)

```text
Storyteller orientation response contract (structural JSON only):
Required root: schema "hg_storyteller_orientation_v1", non-empty information_gaps[] (strings).
Canonical exemplar:
{
  "schema": "hg_storyteller_orientation_v1",
  "information_gaps": ["What tensions are active?", "Which relationships need context?"],
  "trigger": "round_start",
  "temporal_focus": "current",
  "breadth_preference": "broad"
}
Prohibitions: [existing PROHIBITED_STORYTELLER_FIELDS summary]
```

### Proposed manifest / source-kind behavior

- New contribution: `{manifest}:storyteller_orientation_response_contract`, `source_kind=inference_instruction`, priority 28.
- Existing behavioral instruction remains priority 100.
- `response_contract_revision` + digest in provenance (mirror Character).

### Proposed correction / retry behavior

- **Phase 1 (this issue):** No new retry loop required if attempt-0 adherence improves.
- **If needed later:** Add `storyteller_orientation_contract_correction` reusing same projection digest (out of initial scope unless live validation fails).

### Forensic / audit implications

- Structural contribution digest auditable in execution evidence `contribution_ids`.
- No weakening of `schema_mismatch` rejection.
- G2 re-run becomes Storyteller-bound gate validator post-implementation.

### Deterministic test strategy

1. Contract module unit tests: exemplar parses via `parse_storyteller_orientation`.
2. Manifest parity: prepare context includes response-contract contribution with digest.
3. DSH transport-only assertion (extend ownership tests).
4. Regression: `test_storyteller_finalize_transport.py`, `storyteller-orientation-parse-failure.test.mjs`.
5. Mock round: `storyteller-round-integration.test.mjs` (already uses schema wrapper in mocks).

### Bounded live validation strategy

1. Re-run G2 Storyteller infrastructure sentinel only (not full Tier-2).
2. Target: at least one `bound=true` orientation finalize on `deepseek-official` / `deepseek-v4-flash` / `low`.
3. Do **not** run full #136 campaign in #144 scope.

---

## Explicit exclusions

- #136 Character implementation
- #142 transport
- Parser weakening / default orientation fabrication
- Cross-role framework (Option E)
- Full Tier-2 campaign
- Storyteller assessment implementation (unless Governance extends scope after assessment parity review)

---

## Storyteller assessment in #144 scope?

**No** for initial implementation. Assessment shares the same DSH-schema-name / Host-behavioral-only pattern (`storyteller_assessment_context.py` + `buildStorytellerAssessmentPrompt`). Report as **bounded follow-on** if orientation fix pattern is agreed; do not silently expand #144.

---

## Unresolved questions (initial investigation — superseded by refinement below)

1. Should optional orientation fields (`trigger`, `temporal_focus`, `breadth_preference`) be enumerated in the compact contract or left parser-defaulted?
2. Is a single orientation retry (Option D supplement) required if exemplar+projection still fails on `deepseek-v4-flash`?
3. Should DSH pre-finalize `parseStorytellerOrientation` remain or defer entirely to Host finalize (forensic clarity vs duplication)?

---

## Full-weight consensus recommendation (initial)

**Proceed to Governance evaluation.** Evidence supports Type A architectural fix (Option A). No stop conditions triggered. Implementation remains blocked until `consensus_reached`.

---

## Governance refinement (2026-09-06)

Governance accepted investigation (Type A primary, Type C nuance). Option A preferred. This section records challenge/refinement conclusions. **Implementation still NOT authorized** until `consensus_reached`.

### RQ1 — Canonical structural authority: **Pattern 2 (extract declarative structure)**

Mirror Character (#136) layering without circular imports:

```text
v2/domain/modules/storyteller_orientation_response_contract.py
  OWNS (single authority):
    STORYTELLER_ORIENTATION_SCHEMA
    ORIENTATION_TRIGGER_VALUES / TEMPORAL_VALUES / BREADTH_VALUES (frozensets)
    RESPONSE_CONTRACT_REVISION
    CANONICAL_EXEMPLAR (minimal)
    digest + provenance helpers
    project_storyteller_orientation_response_contract_text()
  NO imports from domain_api

v2/domain_api/storyteller_contract.py
  IMPORTS schema + enum frozensets from response_contract module
  KEEPS: PROHIBITED_STORYTELLER_FIELDS (shared with assessment), parser algorithm, dataclasses, KAR mapping
  MAY re-export STORYTELLER_ORIENTATION_SCHEMA for existing import sites

v2/domain_api/storyteller_orientation_context.py
  IMPORTS projection + provenance from response_contract module
  OWNS behavioral instruction contribution only

v2/rp_runtime (DSH)
  transport prompt only; no independent schema authority
```

**Rationale:** `storyteller_contract.py` is parser/service home, not declarative-constant home (unlike Character where ingress is separate). Moving structural constants into `domain/modules/` matches `character_move_response_contract.py` and avoids `domain/modules` importing `domain_api`. `PROHIBITED_STORYTELLER_FIELDS` stays in `storyteller_contract.py` (assessment-shared); projection prose cites abbreviated prohibitions without duplicating the frozenset.

### RQ2 — Minimal model-facing projection

**Include:** `schema`, non-empty `information_gaps[]`, JSON-only/no-markdown (via transport + one line in contract header).

**Exclude from initial projection:** `trigger`, `temporal_focus`, `breadth_preference`, `degradation`, `entity_attention`, `relationship_focus`, `requested_classes`, `narrative_hypothesis`, `orientation_id`, `hg_round_id`, `turn_index` — parser defaults/normalization suffice; live defect did not involve these.

**Proposed exemplar:**

```json
{
  "schema": "hg_storyteller_orientation_v1",
  "information_gaps": [
    "What tensions are active in the scene?",
    "Which relationships need more context?"
  ]
}
```

**Proposed structural prose (Host contribution):**

```text
Storyteller orientation response contract (structural JSON only):
Required root: schema "hg_storyteller_orientation_v1" and non-empty information_gaps[] (strings).
Return one JSON object only. No markdown or commentary.
Canonical exemplar:
<exemplar JSON above, sorted keys>
Do not include mandate fields (next_actor, dialogue, narration, structured_move, continuity mutations, etc.).
```

### RQ3 — DSH boundary

**3A Model-facing prompt:** Reduce to `LIVE_INFERENCE_TRANSPORT_PROMPT` (same as Character). Remove `buildStorytellerOrientationPrompt` semantic lines from cognition path.

**3B Pre-check:** **Option P3** — remove `parseStorytellerOrientation` from `runStorytellerCognition`; always pass `orientationRun.raw` to Host finalize. Host remains sole acceptance authority. Preserves #142 raw-failure pass-through (today pre-check failure already forwards raw). No duplicated schema constant required in DSH runtime path; retain `STORYTELLER_ORIENTATION_SCHEMA` export only for test mocks or move to tiny `storyteller-orientation-constants.mjs`.

### RQ4 — Provenance / digest

**Yes — include**, mirroring #136. Store in `PromptContribution.provenance` (no `metadata` field on `PromptContribution`; provenance is the supported channel). Digest input: deterministic JSON of `{revision, schema, required_fields, exemplar, prohibition_summary}` with sorted keys. **No new `source_kind`.** Manifest projection policy unchanged (`inference_instruction` already allowed).

### RQ5 — Contribution separation

**Yes — two contributions**, both `source_kind=inference_instruction`:

| contribution_id suffix | priority | role |
|------------------------|----------|------|
| `storyteller_orientation_response_contract` | 28 | structural |
| `storyteller_orientation_instruction` | 100 | behavioral |

Matches Character split (28/30); behavioral references "response contract above."

### RQ6 — Retry/correction

**Deferred out of #144 phase 1.** No existing infrastructure makes "no retry" unsafe; current path is single-attempt fail-closed degrade. Retry would mask defective attempt-0 contract.

### RQ7 — Assessment scope

**Orientation only for #144.** Assessment uses separate schema/parser/context/envelope; shared `PROHIBITED_STORYTELLER_FIELDS` import does not force assessment projection changes. Follow-on Issue if live assessment shows same failure class.

### Parser changes

**Minimal:** import `STORYTELLER_ORIENTATION_SCHEMA` and enum frozensets from response_contract; replace inline literal sets in `parse_storyteller_orientation`. **No** acceptance rule changes.

### Proposed production files (implementation cycle)

| File | Action |
|------|--------|
| `v2/domain/modules/storyteller_orientation_response_contract.py` | **Add** |
| `v2/domain_api/storyteller_contract.py` | Import constants; optional re-export |
| `v2/domain_api/storyteller_orientation_context.py` | Add contract contribution |
| `v2/rp_runtime/src/lib/storyteller-cognition-substrate.mjs` | Transport prompt; pass raw only |
| `v2/rp_runtime/src/lib/storyteller-orientation-envelope.mjs` | Remove semantic prompt + production parse (keep manifest bridge; test constants) |
| `v2/rp_runtime/src/lib/live-inference-prompts.mjs` | Optional `LIVE_STORYTELLER_ORIENTATION_PROMPT` alias to transport constant |

### Proposed tests (implementation cycle)

1. `test_issue_144_storyteller_orientation_response_contract.py` — exemplar parses; schema single authority; digest deterministic
2. `test_storyteller_orientation_context.py` or extend S3c — dual contributions + provenance on contract only
3. `test_storyteller_finalize_transport.py` — unchanged pass/fail cases
4. `storyteller-orientation-parse-failure.test.mjs` — update for raw-only finalize path
5. `issue-144-instruction-ownership.test.mjs` — DSH transport-only, no schema prose
6. Manifest projection policy regression — no new inference kinds

### Bounded live validation (post-implementation)

One G2-style orientation sentinel on `deepseek-official` / `deepseek-v4-flash` / `low`. Record SHA, revision/digest, raw output, finalize result, bound state. Target: `accepted=true`, `bound=true`. If schema_mismatch persists with full contract visible in evidence, **STOP** — return to Governance; do not add retries.

### Refinement consensus recommendation

**Full-weight consensus MAY be declared** if Governance accepts Pattern 2 dependency graph, minimal exemplar, P3 DSH pre-check removal, and phase-1 exclusions. Ready for `consensus_reached` transition; implementation still requires explicit authorization after that transition.

---

## Investigation anchors

| Anchor | Value |
|--------|-------|
| G2 orientation evidence | `data/issue136_g2_g3_gates/2026-09-06T23-57-23-541Z/g2-sentinel/execution_evidence/hg-session-410d2366-2ff2-40b1-a924-aadfae4e8525/attempts/d11eb44a-536a-49cc-82f6-8508aba0e4cb.json` |
| G2 gate report | `data/issue136_g2_g3_gates/2026-09-06T23-57-23-541Z/g2-g3-gate-report.json` |
| G3 gate summary | Same report JSON `g3` section; raw attempt not preserved on disk |
| Authoritative parser | `v2/domain_api/storyteller_contract.py` |
| Host prepare | `v2/domain_api/storyteller_orientation_context.py` |
| DSH orchestration | `v2/rp_runtime/src/lib/storyteller-cognition-substrate.mjs` |
| DSH prompt | `v2/rp_runtime/src/lib/storyteller-orientation-envelope.mjs` |
