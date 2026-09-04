# End-to-End Session Quality & Information-Flow Audit — `9065f006`

**Audit:** End-to-End Session Quality & Information-Flow Audit  
**Target session:** `hg-session-9065f006-0dd2-4e93-9dcf-8a6a11c9edaa`  
**Memory scope:** `hg-memory-scope-012c0616-c74f-47c7-95fe-8ec81115e42d`  
**Audit dates:** 2026-09-03 (investigation); 2026-09-04 (Governance challenge + evidence publication)  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full (`docs/issue-bootstrap-profiles.md`)  
**Remediation authorization this cycle:** NONE  
**Evidence fixture:** [`data/fixtures/audit_sqa_e2e_9065f006/`](../../data/fixtures/audit_sqa_e2e_9065f006/)  
**External review:** Greptile independent review via audit persistence PR (see PR link at commit)

---

## Repository anchor (immutable)

| Field | Value |
|-------|-------|
| branch | `main` |
| HEAD SHA | `211e8888edeac58e451cb7ddc9355ab2ec29808c` |
| origin/main SHA | `211e8888edeac58e451cb7ddc9355ab2ec29808c` |
| divergence | `0` ahead / `0` behind |
| working tree at activation | clean |

---

## Scope and method

Read-only investigation at the repository anchor above, crossing:

- Player perceptual visibility (PVR) decomposition and projection
- Opening segmentation and degradation
- Director / Character / Narrator information lanes
- Plot cognition / Librarian contract correction
- Character semantic validation and retry
- Session continuity, user-visible RP quality, and forensic joinability

Evidence sources: canonical session JSON, execution-evidence attempts, investigation tooling (`tools/investigation/`), architecture contracts (`docs/architecture.md`, `docs/audit-workflows.md`, domain modules).

Post-challenge **Governance consensus** incorporated below. **SQA-04a withdrawn** as a separate finding (failure-token impact attributed to SQA-01 and SQA-02a).

---

## Overall conclusion

### System / information flow

**Mostly sound with a major subsystem defect.**

Player perceptual decomposition failed completely in this session (0/18 usable PVR). Designed degradation and most other major runtime systems — opening continuation, Director orchestration, Character semantic guardrails, Narrator rendering, continuity commits — functioned substantially as intended.

### User-visible RP

**Good.**

The session demonstrated strong Ayame fidelity, coherent escalation, continuity, responsive dialogue, meaningful progression, and generally faithful Narrator rendering across 18 player turns.

### Overall session

**Mixed when system integrity and narrative experience are considered together:** good RP produced by a mostly sound runtime containing a major player-perception subsystem defect.

---

## Material findings

### SQA-01 — Player perceptual decomposition inference failure

| Field | Value |
|-------|-------|
| **Classification** | `actual defect` |
| **Recommended disposition** | `remediation_tracked` |
| **Scope** | Failed decomposition inference/validation path only |

**Evidence (mechanical, full session):**

- 18/18 player contributions → PVR `invalid_excluded`
- 0/18 produced usable PVR units
- 36/36 bounded decomposition attempts failed
- Model outputs were **malformed relative to required structured JSON** (markdown prose / fenced blocks instead of schema-conformant JSON)
- ~112,113 reported tokens consumed by unsuccessful decomposition attempts

**Designed downstream failure handling operated correctly (not defective):**

- Neutral unavailable marker projected to Character transcript (`[Player turn — perceptual detail unavailable to this character]`)
- Character interaction trigger omitted
- Player-interaction memory write skipped
- Director `user_turn_source` (full player text) remained available on Director rounds per orchestration contract

The fallback contract is **correct as-is**; the defect is confined to decomposition inference producing unusable structured output.

**Contract references:** `docs/architecture.md` (player PVR #91); `v2/domain/modules/player_perceptual_service.py`; `v2/domain/modules/perceptual_visibility_projection.py`; `v2/domain_api/character_conversation_projection.py`.

**Fixture evidence:** all 36 `player_decomposition` attempts + session PVR records — see manifest `SQA-01`.

---

### SQA-02a — Opening segmentation inference failure

| Field | Value |
|-------|-------|
| **Classification** | `actual defect` |
| **Recommended disposition** | `remediation_tracked` |

Both opening segmentation attempts failed to produce usable segmentation and exhausted their bounded inference allowance:

| Attempt ID | Outcome | Reported tokens |
|------------|---------|-----------------|
| `45936195-d150-4987-9f99-df492d2295df` | `presentation_failed` | 8,866 |
| `f5ec556e-ec40-48f2-8b4e-8ea07384a495` | `presentation_failed` | 8,226 |

Token cost (~17,092 combined) is **impact evidence** for this finding (not a separate SQA-04a finding).

**Fixture evidence:** both opening attempt files + session opening canon — manifest `SQA-02a`.

---

### SQA-02b — Opening degradation/continuation

| Field | Value |
|-------|-------|
| **Classification** | `correct as-is` |
| **Disposition** | `accepted` |

On segmentation failure, runtime preserved authored opening canon and continued session setup per the designed failure contract (`canon_preserved: true` semantics in opening-segmentation phase). No user-visible corruption or session abort.

**Fixture evidence:** session JSON continuation + failed opening attempts — manifest `SQA-02b`.

---

### SQA-03 — Advisory Director reliance under failed player perception

| Field | Value |
|-------|-------|
| **Classification** | `architectural debt` |
| **Recommended disposition** | `monitor` |

**Not** an undeclared or unauthorized information path:

- Director's full `user_turn_source` is legitimate orchestration input (`v2/domain_api/director_context_digests.py`)
- Character's `director_context` is legitimate suggestive/advisory context (`authority_class: suggestive` in `v2/domain_api/character_context_projector.py`)

**Concern:** With PVR uniformly failed, Director advisory `reason` text became **practically important** to coherent Character behavior on Director rounds, while participation-direct rounds lacked equivalent injected player semantics. This creates **fragility under degradation**, not an authority violation.

**Representative turn chains (fixture):**

| Turn | Mode | Key evidence IDs |
|------|------|------------------|
| 1 | Director-led opening | Director `c20c8896-…`, Character `58dbbf6c-…`, Narrator `1af821bd-…` |
| 7 | Participation-direct | `92debfbc-…`, `51cac6a4-…` |
| 11 | Director advisory compensation | `ea6da952-…`, `d1b06ec5-…` |
| 12 | Director + Character (`hg-round-3f65afd6-…`) | Director `b5c38d70-…`, Character orientation `10a0046a-…`, Character move `95c27073-…` |

Turn 1 Character manifest shows neutral PVR marker in `recent_scene_transcript` while `director_context.reason` carries arrival semantics ("Kizzie knocked on the door; Ayame should respond to the arrival."). Turn 7 participation-direct chain shows heavier reliance on scene state and boilerplate participation framing.

**Fixture evidence:** manifest `SQA-03`.

---

### SQA-04b — Plot/Librarian contract-correction friction

| Field | Value |
|-------|-------|
| **Classification** | `architectural debt` |
| **Recommended disposition** | `deferred` |

~20 `plot_cognition_update_contract_correction` passes consumed ~213,335 reported tokens in this session. This indicates schema/contract friction between Plot cognition output and Librarian acceptance worth investigation.

This is **not** a claim that the entire NI stack is wasteful — only that correction-loop volume is materially high.

**Fixture evidence:** complete population of 20 `plot_cognition_update_contract_correction` attempts (token total 213,335 reproducible from published records) — manifest `SQA-04b`. Full 472-file Plot Cognition forensic tree intentionally excluded.

---

### SQA-06 — Character semantic validation/retry

| Field | Value |
|-------|-------|
| **Classification** | `correct as-is` |
| **Disposition** | `accepted` |

Three Character move retries (prior-attempt chains) occurred; all terminal Character commits were accepted after bounded semantic rejection/retry. Rejected generations did not become user-visible corruption.

**Fixture evidence:** session JSON metadata (no dedicated rejection attempt bundle in published packet) — manifest `SQA-06`.

---

## Explicit non-findings and Governance corrections

### SQA-04a — NOT retained

Governance correction: the ~36 failed player-decomposition attempts, ~2 failed opening-segmentation attempts, and ~129k associated failure tokens are **impact evidence for SQA-01 and SQA-02a**. Do not double-count as a separate NI-waste finding.

### Demoted observations (not material findings)

| Topic | Disposition |
|-------|-------------|
| Narrator environmental vocabulary repetition | Investigation candidate |
| General NI-stack invocation volume | Observation only |
| Storyteller marginal contribution | Observation only |
| Environmental cognition frequency in simple scenes | Observation only |

Do **not** recommend Storyteller gating or deterministic speech fallback as accepted remediation from this audit.

---

## Why user-visible RP remained good despite 0% player-PVR success

The session remained narratively coherent because multiple **designed and legitimate** compensation lanes operated together. Success here does **not** make the PVR defect harmless.

### 1. Designed PVR failure degradation

Every player turn received `invalid_excluded` PVR. Character-facing transcript used the neutral unavailable marker; triggers and player-interaction memory writes were correctly suppressed. No alternate unrestricted copy of player posts reached Character manifests.

### 2. Legitimate Director advisory context (Director rounds)

On Director rounds, `director_context.reason` (suggestive) sometimes supplied concise player-action semantics — e.g. Turn 1: arrival/knock framing — while Character still saw only the neutral marker in the perception-filtered transcript. This is authorized advisory context, not a leak of raw player text into Character authoritative lanes.

### 3. Authoritative scene and progression state

`scene_context`, continuity `public_events`, cast role map, and tension/scene-phase fields gave Character stable situational grounding independent of PVR units.

### 4. Character's own committed and narrated history

Prior Ayame dialogue and Narrator-rendered public events accumulated in `recent_scene_transcript` and `public_events`, supplying conversational momentum especially in mid/late session.

### 5. Scene premise and arc inference

The authored household-interview premise (desperate applicant, dominant host) plus escalating committed events (designation, rules, physical compliance beats) provided strong generative priors — especially on **participation-direct** rounds where Director reason carried less player-specific semantics.

### 6. Participation-direct vs Director-round asymmetry

- **Early (Turn 1):** Director reason compensated for absent PVR; Character responded coherently to implied arrival.
- **Middle (Turn 7):** Participation-direct selection; Character relied more on scene state, participation boilerplate ("Forced designation selects eligible actor"), and prior transcript.
- **Late (Turns 11–12):** Escalation arc and committed humiliation/designation beats dominated; Director advisory on Turn 11 still helped bridge a perceptually rich player post; Turn 12 (`hg-round-3f65afd6-…`) shows continued coherence under sustained degradation.

### 7. Narrator faithful rendering

Narrator attempts generally rendered committed Character moves without fidelity failures that would have broken user-visible continuity.

---

## Session summary statistics

| Metric | Value |
|--------|-------|
| Continuity turns | 18 |
| RP history entries | 55 |
| Player PVR total | 18 |
| Player PVR `invalid_excluded` | 18 |
| Player decomposition attempts | 36 |
| Opening segmentation failures | 2 |
| Plot/Librarian contract corrections | 20 |
| Complete execution-evidence attempts (source) | 341 |
| Published fixture attempts | 70 |

---

## Evidence publication

Curated fixture: [`data/fixtures/audit_sqa_e2e_9065f006/`](../../data/fixtures/audit_sqa_e2e_9065f006/)

- Machine manifest: `evidence_manifest.json`
- Human navigation: `README.md`
- Source session SHA-256: `079931022290eb28dc4646492bc72c30a185d24a7ecf4fdb46510e95d6945104`
- Complete index SHA-256: `dff687535b6caadce2dfd64f5768d1502f880f104b32483fc5f10374b48b5ebf`

Published copies: `reasoning_text` stripped; `character_private` and `character_memory` contribution payloads redacted where not required for verification. Runtime originals unchanged. SQA-04b correction count and token aggregate are directly reproducible from the published correction population (see manifest `SQA-04b.reproducibility`).

---

## External verification (Greptile)

Greptile is asked to independently challenge this report and fixture. Review questions are enumerated in the audit persistence PR description. External review is evidence, not governance authority.

---

## Remediation status

**No remediation authorized or filed from this audit cycle.** Dispositions (`remediation_tracked`, `monitor`, `deferred`) are recommendations for future triage only.
