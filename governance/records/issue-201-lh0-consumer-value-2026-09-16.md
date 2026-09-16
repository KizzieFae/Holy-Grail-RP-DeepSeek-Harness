# Issue #201 LH-0 — Final Consumer-Value Qualification Record

**Date:** 2026-09-16  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Candidate SHA:** `4b491e70d5a958aa5a7fb36856f40b50b94122dd`  
**Prior turn-alignment anchor:** `de77f968c70daf0f5c5b07b7466bb9276955ea11`  
**Verification run:** `data/investigation_runs/issue201-lh0-consumer-value-verification-2026-09-16T01-08-28-579Z`  
**LH-1A:** NOT authorized  

---

## P1 remediation (harness-only)

Root cause: LH-0 live path omitted `recordUserTurn` after PVR. Fix: `runPlayerPvrAndRecord()` in `issue201-lh0-live-lib.mjs` — `runPlayerPvr` → `recordUserTurn({ content, player_decomposition, speaker })` → `runA2BeatRound`.

---

## Frozen contract

| Artifact | Value |
|----------|-------|
| Neutral question (core) | What is your policy on overnight guests for live-in staff? I need to know before we discuss a start date. |
| Persistent fact | Overnight guests are not permitted for live-in household staff at this residence. |
| Fixture hash | `e11b360e65ec364c460258df8d882ac0b84be5011fe6eae7e03ed8d5785b19f9` |
| Policy hash | `000c4f091c24b8d3473e1ae24054710bc16c86b11348f11d05ab0a6b32db9a8f` |

Policy T5 realization prefixes role-play framing (`Kizzie meets Ayame's eyes.`) before the frozen neutral question; core wording identical across A/B/C/D.

---

## Deterministic gates

`runLh0ConsumerValueValidationSuite()` — **15/15 PASS** (includes timing 19/19, semantic 28/28).  
Node regressions — `issue201-lh0-player-input.test.mjs` (3/3), `issue201-lh0-timing.test.mjs` (2/2).

---

## Final live tranche (one A/B/C/D each, no retries)

| Arm | Sequence ID | Trigger @ T5 | Guest fact @ T5 | Semantic (S0–S3) | E | F | G | H | LH-1A |
|-----|-------------|--------------|-----------------|------------------|---|---|---|---|-------|
| LH-A | `LH0-LIVE-lh_a-1789520908588` | Yes | Absent | S1 | ✓* | ✓* | ✓* | ✓* | n/a |
| LH-B | `LH0-LIVE-lh_b-1789521295393` | Yes | Present | S3† | ✗ | ✗ | ✗ | ✗ | **No** |
| LH-C | `LH0-LIVE-lh_c-1789521778526` | Yes | Present | S3 | ✓ | ✓ | ✗ | ✓ | **No** |
| LH-D | `LH0-LIVE-lh_d-1789522263172` | Yes | Present | S3 | ✓ | ✓ | ✗ | ✓ | **No** |

\*LH-A counterfactual arm.  
†Semantic read adjudication S3; frozen `lh0_causal_evidence` classifier `consumer_used: false` — E/F/G/H matrix uses classifier contract.

---

## Key findings

1. **P1 fix validated:** All arms show `user_turn_trigger` and `recent_scene_transcript` in Character receipt at T5; Player question reaches cognition (contrast with pre-fix turn-aligned tranche where models reasoned applicant had not asked).
2. **Counterfactual:** LH-A evades stating prohibition; B/C/D committed responses clearly communicate overnight-guest prohibition in presentation text.
3. **Attribution split (LH-B):** Presentation and semantic adjudication show clear policy communication; formal E/F/G/H fail because frozen choice-class marker did not fire (`consumer_used: false`).
4. **G gap (C/D):** Speech-policy consequence in committed response satisfies consumer-value interpretation for G; lifecycle `G_consequential_activation` criterion still fails (no separate state mutation).
5. **K6:** Suspected class remains independently reportable; does not contaminate guest-policy fork.
6. **T6 curfew fork:** Excluded from Character consumer-value adjudication (unchanged).

---

## Forensic progression (preserved)

1. Synthetic apparatus  
2. First live seam failure  
3. Receipt remediation  
4. Semantic projection remediation  
5. Turn-alignment remediation (`de77f96`)  
6. Semantic read-only adjudication  
7. Player-stimulus contract investigation (P1)  
8. **Final consumer-value qualification (this record)**

---

## Governance next decision

Whether any persistent arm (B/C/D) has demonstrated sufficient minimum consumer-value viability for **selective LH-1A authorization** given: (a) harness/input contract now validated; (b) mixed classifier vs semantic adjudication on LH-B; (c) universal G criterion failure on C/D despite clear speech-policy communication.

Do **not** close #201; do **not** authorize production A4→A2, LH-2 freeze, or K6 remediation from this tranche.
