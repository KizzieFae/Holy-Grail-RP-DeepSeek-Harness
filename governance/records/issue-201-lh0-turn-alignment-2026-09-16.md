# Issue #201 LH-0 — Final Turn-Alignment Verification Record

**Date:** 2026-09-16  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Turn-alignment candidate:** `de77f968c70daf0f5c5b07b7466bb9276955ea11`  
**Prior semantic remediation:** `b7d5b7cbecae443d4b308011edbec851e691994d`  
**Verification run:** `data/investigation_runs/issue201-lh0-turn-aligned-verification-2026-09-16T00-12-36-622Z`  
**LH-1A:** NOT authorized  

---

## Root cause (confirmed)

`prepareLh0RoundTransport` and post-commit classification used continuity/runtime `cognitionTurnIndex` for obligation eligibility and lifecycle turns while the harness passed `lh0FixtureTurnIndex` only to character-phase causal evidence. At fixture T5 (guest-policy fork), runtime binding was T4, so `character_due_count` was 0 and semantic receipt occurred one experimental turn late (T6). E/F/G/H failures in the prior qualification tranche were **timing-contaminated**, not fair consumer-cognition adjudication.

---

## Two-clock contract (implemented)

| Clock | Field | Used for |
|-------|-------|----------|
| **LH-0 fixture clock** | `fixture_turn_index` / `lh0FixtureTurnIndex` | Activation predicates, `obligationsForConsumer`, `classifyLh0ObligationStates`, post-commit persistence turns, causal adjudication turn index |
| **Runtime/continuity clock** | `runtime_binding_turn_index` / `cognitionTurnIndex` | Domain manifest `binding.turn_index`, authoritative round identity, audit provenance |

Both clocks are recorded in transport audit and post-commit adapter returns.

**Files:** `issue201-lh0-clocks.mjs`, `issue201-lh0-transport.mjs`, `a2-beat-orchestration.mjs`, `issue201-lh0-post-commit-adapters.mjs`, `issue201-lh0-timing-validation-lib.mjs`

---

## Deterministic pre-run gates

`runLh0TimingValidationSuite()` — **19/19 PASS** (includes prior semantic regressions).  
`runLh0SemanticValidationSuite()` — **28/28 PASS**.  
Node timing tests — **2/2 PASS**.

---

## Fixture / policy hashes

| Artifact | SHA-256 |
|----------|---------|
| `lh0_fixture_manifest.json` | `debf56ac270b4b2d0689aec60e5a58b7d9d6c2012275913a1178dedeea2656d8` |
| `ayame_lh0_policy_v1.json` | `b2b36d57738d82c3fb4273d315a9b9f29b9357b00c01b2e1c87d184bd967a9e2` |

---

## Final verification tranche (one A/B/C/D each, no retries)

| Arm | Sequence ID | A | B | C | D | E | F | G | H | LH-1A |
|-----|-------------|---|---|---|---|---|---|---|---|-------|
| LH-A (control) | `LH0-LIVE-lh_a-1789517556630` | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | ✓* | n/a |
| LH-B | `LH0-LIVE-lh_b-1789517903801` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |
| LH-C | `LH0-LIVE-lh_c-1789518378630` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |
| LH-D | `LH0-LIVE-lh_d-1789518847784` | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | **No** |

\*LH-A counterfactual; persistent-arm criteria marked pass by design.

---

## T5/T6 semantic receipt timing (persistent arms)

| Turn | `fixture_turn_index` | `runtime_binding_turn_index` | `character_due_count` | Receipt | Semantic adequate |
|------|----------------------|------------------------------|----------------------|---------|-------------------|
| T1–T4 | 1–4 | 0–3 | 0 | No | No |
| T5 | 5 | 4 | 2 | Yes (`LH0-OBL-DEFERRED`, `LH0-OBL-LATER`) | Yes |
| T6 | 6 | 5 | 2 | Yes (same IDs) | Yes |

T5 semantic payloads (LH-B sample): guest-permission policy text present in `active_constraints` before Character cognition.

---

## E/F/G/H interpretation (post-alignment)

- **Seam (A–D):** PASS on all persistent arms. Timing correction validated.
- **E/F/G/H:** FAIL on B/C/D. Character received unique semantic information at T5 but `consumer_used` / `decision_influenced` remain false under frozen choice-class markers.
- **Counterfactual:** LH-A and persistent arms show `same_outcome_or_indeterminate` at both forks — no attributable marginal influence demonstrated.
- **Attribution:** Failures are **not** transport/timing seam failures. Classify as **consumer-cognition / evidence-contract** territory: Character did not produce behavior matching `explicit_no_overnight_guests` or `curfew_compatible_duties` markers despite receipt.

### Fixture limitation (T6 curfew fork)

`FORK-EVENING-DUTY-CURFEW` links to `LH0-OBL-IMMEDIATE` (`authorized_consumer: director_turn`). Character never receives curfew semantics in manifest; only director consumer is authorized. T6 E/F/H for curfew cannot be fairly attributed to Character receipt without fixture redesign (out of scope for this authorization).

---

## K6

`k6_class_suspected: true` — anchor projection budget probe; **does not block** obligation chain or qualification execution. Independently reportable.

---

## Entitlement / PVR / fairness

- Entitlement/PVR isolation: **PASS** (no leaks) on all arms.
- C/D arm-neutral manifest merge: **PASS** (D consumer receipt on C and D).
- LH-D fairness enforcement: **PASS** (semantic projection adequate; storyteller absence pass on D).
- LH-C storyteller absence violation noted (1 violation); does not block obligation receipt.

---

## LH-0 completion determination

**LH-0 instrument qualification is substantially complete** for transport, persistence, projection, deferral, and turn-aligned receipt. **LH-1A is NOT ready** — E/F/G/H chain not demonstrated on any persistent arm.

**Do not** close #201 or mark `implemented` under this authorization.

---

## Prior evidence preserved

1. `issue201-lh0-live-2026-09-15T21-16-16-968Z`
2. `issue201-lh0-live-2026-09-15T21-36-09-178Z`
3. `issue201-lh0-cd-postfix-2026-09-15T21-51-52-447Z`
4. `issue201-lh0-final-qualification-2026-09-15T22-17-52-827Z` (timing-contaminated E/F/H)
5. **This turn-aligned tranche**

---

## Governance decision required

Choose among:

1. Accept LH-0 as **instrument-complete** with documented consumer-cognition gaps (no LH-1A).
2. Authorize fixture/evidence-contract revision for T6 curfew Character receipt and/or choice-class sensitivity (not cognition tuning).
3. Authorize LH-1A only if Governance accepts current E/F/G/H negative result as sufficient negative evidence.
