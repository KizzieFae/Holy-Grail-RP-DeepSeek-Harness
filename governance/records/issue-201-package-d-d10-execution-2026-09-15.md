# Issue #201 — D-10 Post-Commit Storyteller vs Plot Execution Record

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Workflow weight:** `full`  
**Status:** Execution complete — **pre-decode blind packet prepared**

**Anchors:**

| Artifact | SHA / path |
|----------|------------|
| D-10 design | `d13f2a0` |
| D-01-L decode | `5d15936` |
| Lineage/VOI | `6ba1459` |
| Execution substrate (pre-harness commit) | `d20feaa` |
| Control substrate | `c751ea6` |
| Harness | `v2/rp_runtime/scripts/issue201-package-d-d10-post-commit.mjs` |
| Policies | `governance/records/issue201-d10-policies/` |

**Primary evidence root:** `data/investigation_runs/issue201-package-d-d10-2026-09-15T01-20-29-181Z/`

---

## 1. Preflight verification

Recorded: `d10_preflight.json`

| Check | Result |
|-------|--------|
| `S4A_ACTIVE_PROPOSAL_KINDS` | `{ issue_tension_pressure }` only |
| `skipLibrarianProposalGeneration` present | Yes |
| Skipped stage semantics | Yes (`stage: 'skipped'`) |
| Plot skip independent | Yes (`skipPlotCognitionOrchestration`) |
| Preamble skip independent | Yes (`skipStorytellerCognition`) |
| Blast radius unchanged | Yes |
| **Verdict** | **PROCEED** |

---

## 2. Frozen player policies

| Policy ID | Hash | Turns | Scenario |
|-----------|------|------:|----------|
| `arkham_d10_policy_v1` | `2533ab9d0addb3b0b14f10af5cd138e14b0f9429157b2077cd32ba681db95ce6` | 5 | Arkham mess hall |
| `ayame_d10_policy_v1` | `be5836d7099fc58547e1e8753fee62f2433ce73677c90f6976797ff104fae26b` | 4 | Ayame household |

Manifest: `d10_policy_manifest.json` in evidence root.

---

## 3. Scenarios executed

| Scenario | Plan | Executed | Notes |
|----------|------|----------|-------|
| Arkham (primary) | 2 seq/arm × 5 turns | 4 sequences | All committed |
| Ayame (confirmatory) | 1 seq/arm × 4 turns | 2 sequences | Calibration passed (≥1 activation on control) |

**Ayame confirmatory arm retained** — control had 1 eligible post-commit activation.

---

## 4. Attempts and replacements

| Failed attempt | Classification | Replacement | In blind packet |
|----------------|----------------|---------------|-----------------|
| `D10-control-arkham_stress-seq1-a1` | generic runtime (`character_failure` turn 1) | `seq1-a2` committed | a2 only |
| `D10-ablated-arkham_stress-seq1-a1` | generic runtime (`character_failure` turn 5) | `seq1-a2` committed | a2 only |
| `D10-control-arkham_stress-seq2-a1` | generic runtime (`character_failure` turn 1) | `seq2-a2` committed | a2 only |

No intervention-specific failure pattern. No expansion triggered.

---

## 5. Post-commit activation (objective)

| Arm | Arkham activations (2 seq) | Ayame activations (1 seq) | Total |
|-----|---------------------------:|--------------------------:|------:|
| Control | 9 (5 + 4) | 1 | **10** |
| Ablated | 0 | 0 | **0** |

All Arkham control sequences had ≥1 activation (threshold met).

---

## 6. Architectural accounting (committed sequences)

### Control arm (3 sequences, 14 turns)

| Metric | Value |
|--------|------:|
| Post-commit ST inferences | 16 |
| ST preamble inferences | 0 |
| Plot inferences | 30 |
| Librarian mediation | 0 |
| Wall time (ms) | 3,270,860 |
| Input tokens | 162,558 |
| Output tokens | 110,909 |
| Reasoning tokens | 74,786 |

### Ablated arm (3 sequences, 14 turns)

| Metric | Value |
|--------|------:|
| Post-commit ST inferences | **0** |
| ST preamble inferences | 0 |
| Plot inferences | 27 |
| Librarian mediation | 0 |
| Wall time (ms) | 3,660,988 |
| Input tokens | 93,834 |
| Output tokens | 86,813 |
| Reasoning tokens | 58,190 |

**Causal isolation:** ablated arm shows zero post-commit Storyteller inference with Plot retained.

---

## 7. Pressure-propagation forensics

Per-turn forensics captured in sequence JSON (`pressure_forensics` block):

- Post-commit hook status and inference ran flags
- Execution-evidence linkage (`storyteller_post_commit_issue_pressure` decisions in evidence root)
- Plot/ST structural comparison scaffolding (Jaccard screening flagged)

**Known limitation:** Domain session file at `data/sessions/{hg_session_id}.json` uses V1 chat schema without embedded `continuity_manager` overlays. Overlay counts in turn forensics may read zero despite post-commit inference running. **Authoritative activation evidence** is execution-evidence post-commit inference records (16 control / 0 ablated). Supplementary overlay extraction from Host fixture persistence recommended before decode if Governance requires overlay text pairs.

---

## 8. Blind packet

| Artifact | Path |
|----------|------|
| Blind sequence packet | `.../outputs/issue201-d10-blind-sequence-packet.json` |
| Concealed answer key | `.../outputs/issue201-d10-blind-sequence-answer-key.json` |
| Labels | SEQ-A … SEQ-F (6 sequences) |
| Blinding integrity | **PASS** (no architecture leakage fields) |

**Do not decode until Governance locks primary scores.**

Transport worksheet: `governance/records/issue201-d10-governance-blind-transport.md`

---

## 9. Expansion status

No expansion authorized or required.

---

## 10. Next Governance action

1. Transport blind packet + scenario briefings to Governance.
2. Score 10 sequence-level dimensions per sequence (SEQ-A…SEQ-F).
3. Lock scores durably.
4. Authorize primary decode.
5. Then evaluate pressure forensics + Plot/ST comparison dataset.

**No architectural verdict until decode.**
