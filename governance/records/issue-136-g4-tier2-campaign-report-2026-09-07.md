# Issue #136 — G4 Full Tier-2 Semantic Validation Campaign Report

**Date:** 2026-09-07  
**Issue:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**PR:** [#137](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/137) OPEN  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  
**Bootstrap profile:** Full  

---

## Activation

| Field | Value |
|-------|-------|
| Starting branch | `issue-136-llm-inference-assessment` |
| Starting / execution SHA | `bc926936b71e61311a9ebebd20fd2f040504f600` |
| PR #137 head (start/end) | `bc92693` |
| `origin/main` | `c04d19ca678bf23f06e4801a97db4376c74efcdb` |
| Issue state | OPEN / `implemented` |
| Project | In Progress / Implemented / P3 |

### Production composition

- Character anchor `8987641` — ancestor ✓
- Storyteller integration `77252e3` — ancestor ✓
- Drift vs G3: **NONE** (same HEAD `bc92693`)
- `proveProductionInferenceUnchanged()` flags `live-inference-prompts.mjs` only — **authorized** Storyteller transport exports + Character/Director transport-only (not material drift)

---

## Deterministic preflight

| Check | Result |
|-------|--------|
| Contract/ownership pytest (36) | **pass** |
| Fixture truth + campaign state + smoke (21) | **pass** |
| Campaign stop-state tests | **pass** (expansion gate, safety guard, stopped scheduling) |

---

## G3 vs campaign matrix (fixture A)

G3 was a **separate pre-campaign authorization slice** (`run-issue136-g3-only.mjs`, evidence under `data/issue136_g2_g3_gates/`). The campaign runner (`runIssue136Tier2Campaign`) does **not** deduct G3 from repetition counts.

| Source | A-STABILITY runs |
|--------|------------------|
| G3 (prior, PASS) | 1 |
| G4 campaign | 3 |
| **Total A evidence** | **4** |

Approved campaign matrix executed in full: **15 fixture runs + 1 sentinel = 16 runs**.

---

## Campaign execution

| Field | Value |
|-------|-------|
| Runner | `v2/rp_runtime/scripts/run-issue136-g4-campaign.mjs` |
| Mode | `live` |
| Provider / model / reasoning | `deepseek-official` / `deepseek-v4-flash` / `low` |
| Evidence root | `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/` |
| Report | `g4-campaign-report.json` |
| Total runs | **16** |
| Total live inferences | **313** (limit 343) |
| Approx. token usage (attempt evidence sum) | **~1,896,345** |
| Campaign state | **completed** (not stopped early) |
| Librarian `deterministic_fallback` | **14/16** runs (all fixture runs except C rep-2; sentinel N/A) |

### Contract revisions / digests (unchanged)

| Role | Revision | Digest |
|------|----------|--------|
| Character | `character_move_response_contract_v1` | `e5192fb3…05651` |
| Orientation | `storyteller_orientation_response_contract_v1` | `7b877b30…c81fd3` |
| Assessment | `storyteller_assessment_response_contract_v1` | `e1c0812f…bedafc` |

---

## Infrastructure summary (all 16 runs)

| Metric | Result |
|--------|--------|
| Character structural acceptance | **15/15** fixture runs committed live Character turn(s) |
| `storyteller.bound` | **16/16** true |
| Orientation finalize accepted | **15/15** fixture runs (sentinel included in bound check) |
| Assessment finalize accepted | **15/15** fixture runs |
| Forbidden entitlement leaks (deterministic) | **0** across all runs |
| Storyteller controlled/mock fallback | **none** on orientation/assessment path |
| Sentinel | **bound=true**, infrastructure PASS |

---

## Per-fixture semantic adjudication

Standard: **fidelity, not valence**. Harness auto-dimensions default `ambiguous`; manual adjudication applied below.

### A — Stable characterization (campaign 3 + G3 1 = 4 total)

| Run | Semantic | Notes |
|-----|----------|-------|
| G3 prior | **PASS** | Guarded boundary; no reconciliation (Governance-accepted) |
| A rep-1 | **PASS** | Trust/wood metaphor; methodical work; no softening |
| A rep-2 | **PASS** | Cautious curiosity; no unwarranted warmth |
| A rep-3 | **PASS** | Staying put; stable routine focus |

**Aggregate: PASS** (4/4)

### B — Legitimate positive change (×2)

| Run | Semantic | Notes |
|-----|----------|-------|
| B rep-1 | **AMBIGUOUS** | Post-restitution: guarded acknowledgment ("I remember") without reconciliation — not failure, not clear positive movement |
| B rep-2 | **PASS** | Engages with Jon's letter; interpersonal opening without instant forgiveness |

**Aggregate: PASS with one ambiguous** (1 PASS, 1 AMBIGUOUS)

### C — Legitimate negative change (×2)

| Run | Semantic | Notes |
|-----|----------|-------|
| C rep-1 | **PASS** | Professional distance; deflection without reconciliation |
| C rep-2 | **PASS** | "Some things don't fix themselves" — earned guarded negativity |

**Aggregate: PASS** (2/2)

### D — Legitimate inaction / refusal (×3)

| Run | Semantic | Notes |
|-----|----------|-------|
| D rep-1 | **PASS** | Observational pause; no forced action |
| D rep-2 | **PASS** | Investigates hum cautiously; legitimate restraint |
| D rep-3 | **PASS** | Accepts quiet; no plot-forcing |

**Aggregate: PASS** (3/3)

### E — Entitlement / knowledge (×2)

| Run | Semantic | Notes |
|-----|----------|-------|
| E rep-1 | **PASS** | Alice does not claim vault code knowledge |
| E rep-2 | **PASS** | Survey purpose stated; no omniscience of silent code entry |

**Aggregate: PASS** (2/2); deterministic leaks **0**

### F — Action-required (×3)

| Run | Semantic | Notes |
|-----|----------|-------|
| F rep-1 | **FAIL** | Key/apron beat; no warning, securing, or protective response to cracking bracket |
| F rep-2 | **FAIL** | Investigates bindery draft; does not address visible colleague hazard |
| F rep-3 | **FAIL** | Explicit non-approach at library lectern; hazard stimulus ignored |

**Aggregate: FAIL** (0/3 PASS; systematic action-avoidance under clear duty stimulus)

### Sentinel (×1)

| Run | Result |
|-----|--------|
| Sentinel | **PASS** — binding intact, no schema regression |

---

## Cross-cutting findings

| Dimension | Finding |
|-----------|---------|
| Unsupported softening | **No material cluster** (A/D stable; B cautious only) |
| Unsupported hardening | **No material cluster** |
| Action avoidance | **Material cluster on F** (3/3) |
| Entitlement/knowledge | **Clean** (0 leaks) |
| Structural/schema | **Clean** (all commits) |
| Provider adherence | Character JSON contract adhered on accepted attempts |
| Librarian degradation | Recurrent partial fallback; did not block binding or most adjudication |
| #136 attribution (F failures) | **Mixed (D/E)** — hazard stimulus present in narrator/fixture truth but Character move did not ground in duty context; may reflect behavioral-invariant salience (#136), scene-stimulus grounding, and/or provider interpretation |
| Unrelated subsystem | No evidence of parser/contract regression |

---

## Campaign-level classification

**D — MIXED / REQUIRES GOVERNANCE REVIEW**

Rationale:

- **Infrastructure gates satisfied:** G1/G2/G3 prior + G4 full matrix completed with Storyteller bound on every run; Character structurally reliable.
- **Semantic campaign:** Strong on stability, inaction, entitlement, and negative-change slices; **material systematic failure on action-required (F)**.
- Not a percentage vote: F recurrence under clear duty stimulus outweighs clean A–E runs for validation readiness on action-fidelity.
- Do **not** force READY FOR FORMAL VALIDATION without Governance review of F failure character and attribution.

---

## Recommendations

1. **Do not** transition #136 to `validated`, merge PR #137, or close #136 based on this campaign alone.
2. Governance should review **F action-required failures** — determine whether follow-on work is #136 behavioral-invariant salience, scene-grounding/orchestration, or bounded provider adherence testing.
3. Apply **streamlined issue policy** before any new Issue: F pattern may warrant #136-associated investigation but is not automatically a separate Issue without Governance scope decision.
4. Librarian `deterministic_fallback` remains an observation; monitor but not campaign-blocking.

---

## Confirmations

| Item | Status |
|------|--------|
| Production remediation performed | **no** |
| #136 validated/merged/closed | **no** |
| #144 / #146 reopened | **no** |
| Unauthorized new Issue | **no** |
| Campaign completed full matrix | **yes** (16/16) |
| Early stop | **no** |
| Retry beyond production correction | **no** |

---

## Evidence index

| Artifact | Path |
|----------|------|
| G4 campaign data | `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/` |
| G4 report JSON | `…/g4-campaign-report.json` |
| G3 prior slice | `data/issue136_g2_g3_gates/2026-09-07T03-34-38-127Z/` |
| G2 prior | `data/issue136_g2_g3_gates/2026-09-07T02-41-04-159Z/` |
| G4 runner | `v2/rp_runtime/scripts/run-issue136-g4-campaign.mjs` |
