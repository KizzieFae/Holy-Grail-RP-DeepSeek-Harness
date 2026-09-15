# Issue #201 G3-C F2 — Arkham Complex-Turn Pre-Decode Comparison Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**F1 classification carried forward:** STRONG A2 SUPPORT (`aee6f98`)  
**Status:** Pre-decode — blind packet prepared; answer key **not opened**

---

## 1. Authorization

G3-C F2 Arkham complex-turn comparison **authorized**. G3-D/E and production: **not authorized**.

---

## 2. Baseline comparability

| Check | Result |
|-------|--------|
| D-07 experimental SHA | `921b127` |
| Arkham spatial fixture changed since D-07 | yes (`perceptual_scene_context`) |
| D-07 Arkham evidence reuse | **no** |
| Decision | paired lean-A4 rerun at current SHA |

Evidence: `data/investigation_runs/issue201-g3c-f2-2026-09-15T06-10-06-991Z/comparability_gate.json`

---

## 3. Sample-E regression

`test_issue_201_g3a_spatial_kernel.py` — **PASS** (Magpie@harley_ivy_table contradiction rejected).

---

## 4. Topology actually used

### A2 F2
Obligation-driven: PVR ingress → eligibility → **Director LLM when Harley+Ivy both eligible** → single Character cognition (selected actor) → commit → Narrator with **mandatory `hg_presentation_spatial_claims_v1` surface** → deterministic spatial validation → presentation validation.

**OFF:** env cognition, char semantic eval, narrator QA, ST, librarian default fan-out, sync plot.

### Lean A4
D-07 ablated baseline with full orientation, char semantic eval, env cognition, librarian mediation, plot init retained.

---

## 5. Run matrix (scored)

| Case | Arm | Objective | Director LLM | Char calls | Spatial surface | Isolation |
|------|-----|-----------|--------------|------------|-----------------|-----------|
| G3C-F2-a2-arkham-r1 | A2 | clean | yes | 1 | yes | pass |
| G3C-F2-a2-arkham-r2 | A2 | clean | yes | 1 | yes | pass |
| G3C-F2-a4-arkham-r1 | lean A4 | clean | — | — | — | — |
| G3C-F2-a4-arkham-r2 | lean A4 | clean | — | — | — | — |

Eligible actors (A2): Harley Quinn + Poison Ivy both runs. Director invoked due to actor ambiguity.

---

## 6. Efficiency (scored runs)

| Metric | A2 (2) | Lean A4 (2) |
|--------|--------|-------------|
| Round sync LLM | 6 | 45 |
| Session inference records | 50 | 134 |
| Input tokens | 15,331 | 160,156 |
| Output tokens | 33,621 | 109,357 |
| Reasoning tokens | 28,330 | 70,660 |
| Operation wall ms | 185,010 | 570,414 |

---

## 7. PVR decomposition note

All runs: ingress `player_decomposition` invoked (shared path). Recorded as **A2 simplification debt**, not modified during G3-C.

---

## 8. Blind packet

- Packet: `.../outputs/issue201-g3c-f2-blind-eval-packet.json`
- Answer key: `.../outputs/issue201-g3c-f2-blind-eval-answer-key.json` — **concealed**
- Report: `.../issue201-g3c-f2-report.json`

---

## 9. Governance next action

Score blind packet (labels A–D). Lock scores before decode. Do not authorize G3-D/E without separate action.
