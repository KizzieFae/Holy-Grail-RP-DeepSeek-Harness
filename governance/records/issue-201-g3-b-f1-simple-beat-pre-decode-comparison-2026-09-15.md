# Issue #201 G3-B F1 — Simple-Beat A2 vs Lean-A4 Pre-Decode Comparison Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Stage:** `consensus_reached` — In Progress / Awaiting Consensus / **P1**  
**Assigned / effective workflow weight:** `full` / `full`  
**G3-A accept SHA:** `b806c7d`  
**Execution SHA:** `b806c7d` (same commit; harness executed at G3-A head)  
**Status:** Pre-decode — blind packet prepared; **answer key not opened**

---

## 1. Authorization scope

Single authorized experiment: **F1 simple-beat** (`ayame_household_entry_evaluation`, F06 stimulus).  
G3-C/D/E, production rollout, production spatial-validator wiring, production A2 activation: **NOT authorized**.

---

## 2. Baseline comparability gate

| Check | Result |
|-------|--------|
| D-07 experimental SHA | `921b127` |
| D-07 control substrate SHA | `c751ea6` |
| `skipNarratorEnvironmentCognition` present | yes |
| Default remains `false` | yes |
| Lean A4 preserves env cognition | yes (skip flag not passed) |
| Material drift vs D-07 Ayame substrate | G3-A spatial-validator + scenario lib + narrator-phase option added |
| **Decision** | **Rerun lean A4 at current SHA** (paired with A2); D-07 ablated evidence **not reused** |

Evidence: `data/investigation_runs/issue201-g3b-f1-2026-09-15T05-37-17-818Z/comparability_gate.json`

---

## 3. Arms

### A2 prototype (G3-A path)

`PVR → eligibility → Character move → validation → commit → Narrator presentation → presentation validation → audit`

Round options: `skipPostCommitPlot`, `skipCharacterKnowledgeCognition`, `skipNarratorEnvironmentCognition` (A2 only).  
Character semantic evaluation: **OFF**.  
Director: deterministic (single eligible actor Ayame).

### Lean A4 ablated (D-07 contract)

`skipStorytellerCognition`, `skipLibrarianProposalGeneration`, `directorSemanticQaEnabled: false`, `narratorSemanticQaEnabled: false`.  
Env cognition, orientation, librarian mediation, plot init, character semantic eval: **present per lean baseline**.

---

## 4. Ayame A2 readiness

| Field | Value |
|-------|-------|
| Case | `G3B-F1-readiness-r0` |
| Verdict | **clean** |
| Committed | yes |
| Presentation | non-empty |
| Two-call topology | yes |
| Round-scoped prohibited cognition | pass |

---

## 5. Run matrix (scored)

| Case ID | Arm | Rep | Objective | Session |
|---------|-----|-----|-----------|---------|
| `G3B-F1-a2-ayame-r1` | A2 | 1 | clean | `hg-session-ffd361ca-3e6a-4e6d-82fd-d1dbd1360295` |
| `G3B-F1-a2-ayame-r2` | A2 | 2 | clean | `hg-session-bc89a02f-bd68-4d75-8d64-6970756468aa` |
| `G3B-F1-a4-ayame-r1` | lean A4 | 1 | clean | `hg-session-4b4cb89b-3c99-4332-9676-dfceb842dd39` |
| `G3B-F1-a4-ayame-r2` | lean A4 | 2 | clean | `hg-session-7bc17b6d-c869-4bb9-bab3-672c168ac909` |

Readiness run excluded from blind packet. **No replacement runs.**

---

## 6. Objective correctness

All four scored runs: committed turn, non-empty presentation, PVR valid (lean A4), hook isolation (lean A4), A2 round-scoped prohibited cognition absent, A2 two-call topology proof pass.

**Spatial validator:** exercised contract path; live Narrator outputs prose-only → `no_structured_spatial_claims_surface` (not failure; zero contradictions).

---

## 7. Character semantic-eval-off (A2)

| Run | Move committed | Semantic eval inferences | Coherent presentation |
|-----|----------------|--------------------------|----------------------|
| r1 | yes | 0 | yes |
| r2 | yes | 0 | yes |

No defect observed that deterministic validation missed.

---

## 8. Environment-cognition-off (A2)

| Run | Env cognition inferences (round) | D-04R note |
|-----|-------------------------------|------------|
| r1 | 0 | deferred to Governance blind adjunct |
| r2 | 0 | deferred to Governance blind adjunct |

Lean A4 ran env cognition (1–2 calls/run); A2 presentations still include threshold/door/hall grounding from Narrator without env-cognition stage.

---

## 9. Efficiency accounting (scored runs)

| Metric | A2 (2 runs) | Lean A4 (2 runs) |
|--------|-------------|------------------|
| Session inference records | 44 | 78 |
| Round-scoped sync LLM (A2) | 5 (incl. 1 char retry r1) | — |
| Operation wall ms total | 105,368 | 252,510 |
| Player-visible critical path ms (A2) | 21,871 / 20,425 | n/a (latency recon incomplete) |
| Input tokens | 11,020 | 74,044 |
| Output tokens | 16,422 | 48,575 |
| Reasoning tokens | 12,725 | 27,534 |
| Handoff estimate (architectural) | 4 | 78 |

**Wall-time caveat:** path variance and ingress PVR decomposition dominate session totals; compare call topology directly.

---

## 10. Decision-value (A2 round)

Mandatory endpoints only: `character_move` → commit; `narrator_presentation` → player output. No optional cognition restored.

**Lean A4 extra cognition (not in A2):** plot_cognition_init, director_decision, character_orientation, character_semantic_evaluation, narrator_environment_cognition, librarian_mediation (1–6 calls/run).

---

## 11. Blind packet disposition

| Artifact | Path |
|----------|------|
| Evidence root | `data/investigation_runs/issue201-g3b-f1-2026-09-15T05-37-17-818Z` |
| Execution report | `.../issue201-g3b-f1-report.json` |
| Blind packet | `.../outputs/issue201-g3b-f1-blind-eval-packet.json` |
| Concealed answer key | `.../outputs/issue201-g3b-f1-blind-eval-answer-key.json` — **NOT OPENED** |
| Transport | `.../outputs/issue201-g3b-f1-blind-eval-transport.md` |
| Harness | `v2/rp_runtime/scripts/issue201-g3-b-f1-simple-beat.mjs` |

Rubric: `governance/records/issue201-stage2-human-evaluator-worksheet.md` (11 dimensions + adjuncts).

---

## 12. Stop conditions

**Not triggered.** Ayame traversed A2 path without restoring prohibited cognition.

---

## 13. Governance next action

Score blind packet (labels A–D) per 11-dimension rubric + adjuncts. **Lock scores before decode.** Implementation AI must not open answer key or compute architecture semantic means pre-lock.

---

## 14. Verdict status

`not_rendered_pending_governance_blind_lock`
