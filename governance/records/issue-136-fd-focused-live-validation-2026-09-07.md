# Issue #136 — Corrected F×3 + D×2 Focused Live Validation Report

**Date:** 2026-09-07  
**Issue:** [#136](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/136)  
**PR:** [#137](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/pull/137) OPEN  
**Execution SHA:** `a7cc5a0`  
**Fixture encoding:** `opening_pvr_turn_zero_v1`  
**Assigned workflow weight:** `standard`  
**Effective workflow weight:** `full`  

---

## Activation

| Field | Value |
|-------|-------|
| Branch | `issue-136-llm-inference-assessment` |
| Local / remote / PR head | `a7cc5a0` |
| `origin/main` | `c04d19c` |
| Issue | OPEN / implemented |
| Project | In Progress / Implemented / P3 |
| Production drift | None (validation tooling + records only) |

## Deterministic pre-live gate

| Check | Result |
|-------|--------|
| F manifest gate (opening → PVR → transcript) | **PASS** |
| D manifest gate | **PASS** |
| Entitlement negative control | **PASS** |
| Premise/opener separation | **PASS** |
| Focused tests (15/15 pre-live subset) | **PASS** |

## Focused runner bounds

| Field | Value |
|-------|-------|
| Runner | `v2/rp_runtime/scripts/run-issue136-fd-focused.mjs` |
| Authorized matrix | F×3 + D×2 |
| Actual runs | **5** |
| Sentinel / A–E | **not scheduled** |
| Safety envelope | max 7 runs / 88 inferences |
| Actual inferences (limits counter) | **52** |
| Campaign state | **completed** (no early stop) |

## Live configuration

| Field | Value |
|-------|-------|
| Provider | `deepseek-official` |
| Model | `deepseek-v4-flash` |
| Reasoning | `low` |
| Token usage (instrumentation sum) | ~486,415 input / ~367,085 output (~853,500 total) |

## Evidence root

`data/issue136_tier2_campaign/live/fd-focused-2026-09-07T05-44-04-343Z/`

Report JSON: `fd-focused-live-report.json`

Historical malformed G4 root (not combined): `data/issue136_tier2_campaign/live/2026-09-07T03-40-45-925Z/`

---

## Run matrix

### F rep-1

| Field | Value |
|-------|-------|
| Run ID | `issue136-136-T2-F-ACTION-REQUIRED-r1-3800673c-9431-4aee-bf03-dc82bce377db` |
| Session | `hg-session-d5af3e2f-edbe-4fc6-83a5-8c2204a67323` |
| Round | `hg-round-afba2877-8269-4be4-8bc5-0008fc386fd2` |
| Fixture validity | **VALID** — `recent_scene_transcript` contains bracket/colleague crack prose (priority 16); no `scene_setup` |
| Character structure | **PASS** — `hg-commit-598256fd-e60c-4659-8b13-14317780348f` |
| Storyteller | **BOUND** — orientation accepted; assessment accepted |
| Director cue | Unrelated refrigerator hum (`environment_event`) |
| Semantic | **PASS** — braces cracked bracket, warns colleague |
| Overall | **PASS** |

### F rep-2

| Field | Value |
|-------|-------|
| Run ID | `issue136-136-T2-F-ACTION-REQUIRED-r2-78899b66-777b-4e89-94c8-0e5e4dacf734` |
| Session | `hg-session-db314446-24aa-4440-8e44-a8111cef1913` |
| Round | `hg-round-d76a4390-2709-4ac4-a1d5-5a41b13fbde5` |
| Fixture validity | **VALID** |
| Character structure | **PASS** — `hg-commit-c45bd591-e87a-4332-9e56-578c6e6ea432` |
| Storyteller | **BOUND** |
| Director cue | Empty / minimal advisory |
| Semantic | **PASS** — wedges prop under failing bracket, orders colleague back |
| Overall | **PASS** |

### F rep-3

| Field | Value |
|-------|-------|
| Run ID | `issue136-136-T2-F-ACTION-REQUIRED-r3-6af54080-4137-451f-b651-0022bf86d487` |
| Session | `hg-session-2cd803d9-c640-4e67-8e23-186fdb064165` |
| Round | `hg-round-4ea6b047-250f-4ef8-adb3-66677b1123a9` |
| Fixture validity | **VALID** |
| Character structure | **PASS** — `hg-commit-09b81ca8-bdb7-43fc-a431-f5dc8d6cda68` |
| Storyteller | **BOUND** |
| Semantic | **PASS** — identifies stress fracture, urges station clearance before collapse |
| Overall | **PASS** |

**F aggregate: PASS (3/3)**

### D rep-1

| Field | Value |
|-------|-------|
| Run ID | `issue136-136-T2-D-INACTION-r1-cd0b0ba9-34f0-484a-bea5-20c64a8128e7` |
| Session | `hg-session-ae8039cc-e699-47a4-8dc3-4ee97577205d` |
| Round | `hg-round-d54623fa-8382-4014-bd16-31b7c4ec9bb5` |
| Fixture validity | **VALID** — scraping/panel prose in `recent_scene_transcript` |
| Character structure | **PASS** — `hg-commit-4083fe2b-c800-4d50-82e9-586f354822dc` |
| Storyteller | **BOUND** |
| Director cue | Coolant-pipe hum (atmospheric; does not confirm emergency) |
| Semantic | **PASS** — listens, defers escalation, marks for later inspection |
| Overall | **PASS** |

### D rep-2

| Field | Value |
|-------|-------|
| Run ID | `issue136-136-T2-D-INACTION-r2-b45ddcf3-2752-4459-94e8-8f493906323d` |
| Session | `hg-session-37e5e4bb-0377-4fc3-9085-bb29da5a7a91` |
| Round | `hg-round-a10ed9c6-1ee5-40bb-9e5f-d0840ed6df8d` |
| Fixture validity | **VALID** |
| Character structure | **PASS** — `hg-commit-83bc6754-5554-4f40-8cd8-bc6564195931` |
| Storyteller | **BOUND** |
| Semantic | **PASS** — pauses, listens, considers benign explanations, cautious inspection without alarm |
| Overall | **PASS** |

**D aggregate: PASS (2/2)**

---

## F/D discrimination

**Classification: CLEAR DISCRIMINATION**

All F runs produced immediate protective/bracing/clearance responses grounded in the perceived bracket hazard. All D runs preserved proportionate restraint, observation, and deferred escalation under ambiguous scraping. The system distinguished action-required hazard from low-urgency uncertainty.

## Historical G4 comparison

| Family | Malformed G4 (harness) | Corrected focused slice |
|--------|------------------------|-------------------------|
| F | 0/3 FAIL (stimulus absent from Character context) | **3/3 PASS** (stimulus present; protective action) |
| D | 3/3 PASS (not stimulus-faithful) | **2/2 PASS** (stimulus present; legitimate restraint) |

G4 F failures are reclassified as **fixture-encoding artifact**, not demonstrated production action-selection defect under valid perception.

## Semantic evaluator observations

- `character_semantic_qa` **not invoked** on any run (0 attempts).
- No correction-time action-avoidance dimension fired.
- Moves committed on first `character_move` attempt without semantic QA gate.
- Evaluator expansion for action-avoidance remains **informative but not proven necessary** for this slice (F passed without it).

## Director substitution observations

- F rep-1: unrelated refrigerator `environment_event` present; Character still acted on bracket hazard from PVR transcript.
- Other runs: Director cues atmospheric/minimal; did not erase fixture stimulus from Character manifest.
- No evidence Director mediation is required for perception — canonical PVR path sufficient.

## Revised root-cause conclusion

Under corrected opening+PVR encoding, **no production Character projector or action-selection defect is demonstrated**. Historical F 0/3 reflected **validation harness authority-encoding failure (F2/F3)**, not faithful inference under valid stimulus.

## Recommendations

1. **Do not** merge PR #137 or close #136 solely on this slice — full Tier-2 rerun and Governance review still required for broader matrix.
2. **Do not** treat G4 F/D semantics as equivalent to this slice.
3. Consider semantic-evaluator action-avoidance dimension as **follow-on within #136** if future F failures recur under valid encoding.
4. **Full Tier-2 rerun:** defer to Governance; infrastructure now supports corrected F/D encoding.

## Confirmations

| Item | Status |
|------|--------|
| Exactly F×3 + D×2 live runs | **yes** |
| No other live fixtures | **yes** |
| No remediation during slice | **yes** |
| #136 OPEN / PR #137 unmerged | **yes** |
| #144 / #146 CLOSED | **yes** |
| No unauthorized Issue | **yes** |

**STOP — return to Governance.**
