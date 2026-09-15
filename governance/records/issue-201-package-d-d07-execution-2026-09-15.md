# Issue #201 — D-07 Narrator Semantic-QA Execution & Pre-Decode Report

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full` / `full`  
**Status:** Execution complete — **pre-decode blind packet prepared**

| Anchor | SHA / path |
|--------|------------|
| D-07 design | `b88333b` |
| Harness | `v2/rp_runtime/scripts/issue201-package-d-d07-narrator-qa.mjs` |
| Control substrate | `c751ea6` |
| Evidence root | `data/investigation_runs/issue201-package-d-d07-2026-09-15T04-25-04-321Z/` |

---

## 1. Activation / state / weights

| Field | Value |
|-------|-------|
| D-04R | Accepted (`b88333b`) |
| D-07 design | Accepted (refined classification rules) |
| D-07 execution | **Authorized and complete** |
| Final synthesis | **Paused** pending D-07 blind decode |
| Production remediation | **NOT authorized** |
| Verdict / classification | **NOT rendered** (pre-decode) |

---

## 2. Substrate / harness SHA

| Item | Value |
|------|-------|
| `git rev-parse HEAD` at execution start | `b88333b324c6324d5a3951120fc1aa7e15b42b99` |
| Harness | `issue201-package-d-d07-narrator-qa.mjs` |
| Report schema | `issue201_package_d_d07_execution_v1` |

---

## 3. Hook preflight

`d07_preflight.json` — **PROCEED**

| Check | Result |
|-------|--------|
| `narratorSemanticQaEnabled` wired | pass |
| Narrator phase skip gate | pass |
| Director QA independent | pass |
| ST preamble skip independent | pass |
| Post-commit skip independent | pass |
| Plot skip independent | pass |

**Runtime isolation (scored runs):** 8/8 `hook_isolation.isolation_ok === true`

- Control: `narrator_semantic_qa` observed 1–2 per run; Director QA 0; post-commit ST 0
- Ablated: `narrator_semantic_qa` observed **0** on all scored runs

---

## 4. Exact topology (both arms)

| Layer | Setting |
|-------|---------|
| Storyteller preamble | OFF |
| Storyteller post-commit | OFF |
| Plot | ON |
| Director semantic QA | OFF |
| Character orientation | ON |
| Narrator environment cognition | ON |
| Librarian mediation | Normal |
| **Narrator semantic QA** | **ON (control) / OFF (ablated)** |

---

## 5. Executed runs (scored set)

| Case ID | Arm | Scenario | Committed | Objective | Narrator QA |
|---------|-----|----------|:---------:|-----------|------------:|
| D07-control-arkham_stress-r1 | control | Arkham | yes | clean | 2 |
| D07-control-arkham_stress-r2 | control | Arkham | yes | clean | 2 |
| D07-control-ayame_controlled-r1 | control | Ayame | yes | clean | 1 |
| D07-control-ayame_controlled-r2 | control | Ayame | yes | clean | 2 |
| D07-ablated-arkham_stress-r1 | ablated | Arkham | yes | clean | 0 |
| D07-ablated-arkham_stress-r2-a2 | ablated | Arkham | yes | clean | 0 |
| D07-ablated-ayame_controlled-r1 | ablated | Ayame | yes | clean | 0 |
| D07-ablated-ayame_controlled-r2 | ablated | Ayame | yes | clean | 0 |

**Total scored:** 8 (per design, with one replacement)

---

## 6. Failures / replacements

| Failed attempt | Classification | Replacement | In blind packet |
|----------------|----------------|-------------|-----------------|
| `D07-ablated-arkham_stress-r2` | `character_failure` (generic runtime; no presentation) | `D07-ablated-arkham_stress-r2-a2` | **a2 only** |

- Not intervention-specific (round failed before narrator lane on ablated arm).
- Failed run **excluded** from blind packet; meta retained in evidence root.

---

## 7. Objective correctness results

| Arm | Clean | Degraded | Blocking (scored set) |
|-----|------:|---------:|--------------------:|
| Control | 4 | 0 | 0 |
| Ablated | 4 | 0 | 0 |

All scored runs: PVR `valid`, round committed, non-empty presentation.

**No objective regression observed on ablated arm** in scored set (post-replacement).

---

## 8. QA control-arm intervention summary (D-07 new runs)

| Metric | Value |
|--------|------:|
| QA invocations | 7 |
| Presentations with QA metadata | 7 |
| `pass` (first-attempt accept) | 6 |
| `soft_regen` | 1 |
| `hard_regen` | 0 |
| `residual_accept` | 0 |
| `authorship_fail_closed` | 0 |
| **Non-pass total** | **1** |

### Notable intervention (control ayame-r2)

1. **soft_regen** on attempt 0 — findings: player-authorship soft overreach (house number visibility), environmental repetition, framing distortion.
2. Narrator **regenerated** (attempt 1) → **pass** with revised presentation (threshold framing without unsupported house-number visibility claim).
3. **Forensic note:** QA triggered regen; final presentation differs from pre-QA candidate. Objective defect correction: **soft subjective/authorship framing** (not blocking). Whether ablated arm would have published attempt 0 unchanged — **not directly observed** (requires decode comparison; do not pre-classify).

**Arkham control:** 4/4 QA passes, no regen.

---

## 9. D-10 archive intervention summary (supplement)

**Governance baseline (accepted):** 64 presentations; 9 non-pass events (3 hard_regen + 5 soft_regen + 1 authorship_fail_closed + 1 accept_with_residuals).

**Re-parse from available D-10 execution evidence** (`issue201-package-d-d10-2026-09-15T01-20-29-181Z`):

| Category | Re-parsed count |
|----------|----------------:|
| Presentations with QA decision metadata | 33 |
| `pass` | 27 |
| `soft_regen` | 3 |
| `hard_regen` | 2 |
| `residual_accept` | 1 |
| **Non-pass total** | **6** |

**Overlap resolution:** `residual_accept` is **not** counted in `pass`; non-pass = all events where `policy_action !== pass` (includes residual_accept, regen, authorship). Re-parse corpus is **partial** (33/64) because longitudinal sequence evidence is not fully indexed in presentation-decision sidecars from this harness pass — **Governance D-10 counts remain authoritative** for archive scale; D-07 re-parse confirms intervention **does occur** under control topology.

---

## 10. Intervention-value forensic readiness

Per-run QA forensics JSON: `outputs/D07-*-qa-forensics.json`

Captured fields (where available): invocation, policy_action, category, findings, pre-QA candidate, final presentation, validation class, retry decision, QA wall/tokens.

**Ready for post-decode adjudication** of:

- consequential benefit rate (control interventions)
- protected-outcome necessity vs topology (Governance refinement §9)

**Not rendered in this report.**

---

## 11. Inference accounting

| Arm | Runs | Total inferences | Narrator QA | Narrator env | Narrator regen (presentation attempt_index>0) |
|-----|-----:|-----------------:|------------:|-------------:|----------------------------------------------:|
| Control | 4 | 227 | 7 | 10 | 1 |
| Ablated | 4 | 227 | **0** | 10 | 0 |

Causal isolation: ablated arm eliminates all `narrator_semantic_qa` calls with matched env cognition count.

---

## 12. Token / reasoning accounting

| Arm | Input tokens | Output tokens | Reasoning tokens |
|-----|-------------:|--------------:|-----------------:|
| Control | 254,804 | 155,630 | 102,959 |
| Ablated | 231,552 | 168,153 | 111,962 |

QA-specific (control): ~11.8s summed QA wall across 7 invocations (per-attempt evidence).

---

## 13. Wall-time accounting

| Arm | Total operation wall (ms) | Mean per run (ms) |
|-----|--------------------------:|------------------:|
| Control | 754,634 | 188,659 |
| Ablated | 824,651 | 206,163 |

**Not interpreted as causal QA savings** — high run-to-run variance (ablated arkham-r1 269s vs r2-a2 304s; failed r2 101s incomplete). Librarian fan-out and character-path variance dominate.

---

## 14. Contamination / confounds

| Item | Assessment |
|------|------------|
| Hook blast radius | No drift detected |
| Director QA | OFF both arms |
| ST layers | OFF both arms |
| Generic runtime failure | 1 ablated Arkham rep — **replaced** |
| Librarian fan-out variance | Present; not blind endpoint |
| Single-turn sample | Low intervention rate expected; D-10 supplement required for intervention architecture question |

**No stop condition triggered.**

---

## 15. Blind-packet integrity check

| Check | Result |
|-------|--------|
| Samples | 8 (A–H) |
| Randomized | yes |
| Architecture/arm/QA/session/latency fields in packet | **absent** |
| Forbidden substring scan | **PASS** (after instruction wording fix) |
| Decode performed | **NO** |

---

## 16. Blind packet

**Path:** `data/investigation_runs/issue201-package-d-d07-2026-09-15T04-25-04-321Z/outputs/issue201-d07-blind-eval-packet.json`

**Schema:** `issue201_blind_eval_packet_v1`  
**Rubric:** Stage-2 11-dimension + optional adjunct (`environmental_grounding`, `overall_rp_usefulness`)

**Transport:** `governance/records/issue201-d07-governance-blind-transport.md`

---

## 17. Concealed answer-key path

`data/investigation_runs/issue201-package-d-d07-2026-09-15T04-25-04-321Z/outputs/issue201-d07-blind-eval-answer-key.json`

**Do not open until Governance locks scores.**

---

## 18. Evidence root

`data/investigation_runs/issue201-package-d-d07-2026-09-15T04-25-04-321Z/`

| Artifact | Path |
|----------|------|
| Machine report | `issue201-package-d-d07-report.json` |
| Preflight | `d07_preflight.json` |
| Presentations | `outputs/D07-*-presentation.txt` |
| QA forensics | `outputs/D07-*-qa-forensics.json` |
| Blind packet | `outputs/issue201-d07-blind-eval-packet.json` |

---

## 19. Durable record / commit / Issue comment

This document + harness commit. Evidence under `data/investigation_runs/` (gitignored).

---

## 20. Decode / synthesis confirmation

| Action | Status |
|--------|--------|
| D-07 live execution | **Complete** |
| Blind packet to Governance | **Ready** |
| Answer-key decode | **NOT performed** |
| D-07 architectural classification | **NOT rendered** |
| #201 synthesis | **NOT begun** |
| Production QA / env tiering changes | **NOT authorized** |

---

## Next Governance action

1. Score blind packet A–H (Stage-2 rubric).
2. Lock scores durably.
3. Authorize primary decode.
4. Apply refined classification rules (protected-outcome vs topology).

**Issue #201 remains:** `investigating` — In Progress / Investigating / **P1**
