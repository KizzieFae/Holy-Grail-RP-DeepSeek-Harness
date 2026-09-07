# Issue #136 — Formal Validation Report (Composite Tier-2 Evidence)

**Date:** 2026-09-07  
**Issue:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**PR:** [#137](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/137) OPEN (unmerged)  
**Formal-validation candidate SHA:** `373436d`  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  

---

## Classification

**A — VALIDATION PASS**

---

## Candidate integrity

| Field | Value |
|-------|-------|
| Branch | `issue-136-llm-inference-assessment` |
| Candidate SHA | `373436d` |
| `origin/main` | `c04d19c` |
| Production implementation anchor | `f679dc4` (Character response contract + instruction ownership) |
| Storyteller stack | `#144` + `#146` integrated on branch / `main` ancestor `77252e3` |

Post-G4 deltas (`a7cc5a0`, `373436d`) are **validation harness, fixtures metadata, tests, runners, and records only**. No production Character/Director/Storyteller/Librarian inference behavior changes.

`proveProductionInferenceUnchanged()` at `373436d`: only authorized `live-inference-prompts.mjs` Storyteller transport exports differ from implementation anchor — **non-material**, previously accepted at G2 composition.

---

## Evidence-reuse policy

Composite acceptance per Governance authorization. Reuse permitted where:

1. production behavior under test is unchanged on candidate;
2. fixture semantics unchanged or superseded only for malformed F/D;
3. provenance SHA and evidence root documented;
4. prior Governance acceptance recorded.

| Gate | Source SHA | Evidence root | Reuse basis |
|------|------------|---------------|-------------|
| G1 structural | `f679dc4`–`8987641` | implementation-validation record | Production contracts unchanged |
| G2 Storyteller-bound | `ccb5158` / `af0a26d` | `data/issue136_g2_g3_gates/2026-09-07T02-41-04-159Z/` | ST path unchanged; transport-only diff authorized |
| G3 A-stability | `bc92693` | `data/issue136_g2_g3_gates/2026-09-07T03-34-38-127Z/` | A fixture independent of F/D opener encoding |
| G4 A/B/C/E/sentinel | `c677567` | `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/` | Retained except F/D semantic claims |
| F corrected | `a7cc5a0` | `…/fd-focused-2026-09-07T05-44-04-343Z/` | Authoritative F acceptance |
| D corrected | `a7cc5a0` | same | Authoritative D acceptance |

**Excluded from acceptance:** historical G4 F 0/3 and G4 D 3/3 as stimulus-faithful evidence.

---

## Final semantic matrix

| Family | Evidence | Reps | Validity | Result | Qualification |
|--------|----------|------|----------|--------|---------------|
| **A** | G3×1 + G4×3 | 4 | VALID | **PASS** | Stable characterization; no softening/hardening cluster |
| **B** | G4 | 2 | VALID | **PASS** (1 AMBIGUOUS retained) | Turn-0 Jon restitution seeded via `JON_RESTITUTION_MOVE` commit; turn-1 live Mara |
| **C** | G4 | 2 | VALID | **PASS** | Turn-0 betrayal mock commit; turn-1 live Mara |
| **D** | Focused slice only | 2 | VALID | **PASS** | PVR scraping/panel; proportionate restraint |
| **E** | G4 | 2 | VALID | **PASS** | 0 entitlement leaks |
| **F** | Focused slice only | 3 | VALID | **PASS** | PVR bracket hazard; protective responses 3/3 |
| **F/D discrimination** | Focused slice | — | — | **CLEAR** | Action vs restraint distinguished |
| **Sentinel** | G4 | 1 | VALID | **PASS** | Infrastructure/binding intact at G4 SHA; no relevant production drift since |

### B authoritative progression trace

```text
JON_RESTITUTION_MOVE (turn 0 mock) → domain commit → continuity
→ Mara turn-1 manifest → adjudicated response
```

Does **not** depend on malformed opener-only F/D path. B rep-1 remains **AMBIGUOUS** (guarded acknowledgment); aggregate still supports positive-change objective (1 PASS + 1 AMBIGUOUS).

### C authoritative progression trace

```text
JON_BETRAYAL_MOVE (turn 0 mock) → domain commit → continuity
→ Mara turn-1 manifest → negative-change response
```

---

## Infrastructure

| Metric | Result |
|--------|--------|
| Storyteller bound (focused F/D) | 5/5 |
| Orientation finalize | accepted 5/5 |
| Assessment finalize | accepted 5/5 |
| Librarian partial degradation | Recurrent; **non-blocking** — did not impair adjudication |
| Infrastructure-invalid runs | 0 |

---

## Semantic-evaluator disposition

**NON-BLOCKING OBSERVATION** — `character_semantic_qa` not invoked on corrected F/D slice; action avoidance not a correction-time dimension. Not required for #136 acceptance per Governance position.

---

## Architecture consensus checklist (18/18)

All Full-consensus architecture items satisfied at candidate SHA (Domain-owned response contract, Host structural projection, DSH transport-only, separate contributions, correction parity, Character-only scope, fidelity-not-valence, legitimate change/inaction/action envelopes, entitlement boundaries).

---

## Deterministic validation (candidate SHA `373436d`)

| Command | Result |
|---------|--------|
| `pytest` contract + ownership (36 tests) | **36 passed** |
| `node --test` issue136 focused suite (29 tests) | **29 passed** |

---

## Historical malformed evidence treatment

G4 F/D semantic results preserved as **forensic historical evidence** under malformed harness encoding. Formal acceptance uses **corrected focused slice only** for F/D.

---

## Formal validation outcome

**VALIDATION PASS** — composite evidence satisfies #136 Tier-2 semantic objectives. Issue advanced `implemented` → `validated`. PR #137 remains unmerged; closure not authorized.
