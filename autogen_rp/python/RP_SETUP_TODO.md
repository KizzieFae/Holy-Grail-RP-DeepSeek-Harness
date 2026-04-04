# Phase 3.3 — Quality Assessment & Tuning

**Goal:** Improve RP quality on top of the now-stable runtime without changing core architecture or introducing new subsystems.

---

## A. Scope — Scene movement

- [ ] Evaluate progression naturalness
- [ ] Evaluate stall / plateau behavior
- [ ] Evaluate handoff quality
- [ ] Evaluate continuation / Director / override / fairness interaction

---

## B. Scope — Character performance

- [ ] Evaluate voice vitality
- [ ] Evaluate emotional sharpness
- [ ] Evaluate instruction drag / prompt crowding
- [ ] Evaluate social plausibility

---

## C. Scope — Scene readability

- [ ] Evaluate narrator flow
- [ ] Evaluate turn-to-turn readability
- [ ] Evaluate procedural vs natural prose feel

---

## D. Current baseline entering this phase

- [x] Architecture-quality harness implemented
- [x] A1 / B / C comparison variants implemented
- [x] No clear evidence of over-layering from architecture runs
- [x] `resolve_progression_override_actor` identified as only repeatable structural-effect layer
- [x] Turn-selection v1 policy refinement accepted:
  - [x] C2 continuation suppression when last spotlight matches
  - [x] Explicit P1 vs P3/P4 guards
  - [x] Validation + attribution alignment

---

## E. Tuning order

### 1. Selection / handoff

- [ ] Validate current selection hierarchy quality in practice
- [ ] Monitor `continuation_override_skipped_c2` frequency and effect
- [ ] Identify remaining same-speaker stacking issues
- [ ] Identify awkward spotlight jumps
- [ ] Refine override policy **only if repeated quality evidence supports it**

---

### 2. Character prompt quality

- [ ] Review prompt density / instruction drag
- [ ] Evaluate ordering and emphasis of prompt sections
- [ ] Confirm character voice remains distinct and sharp
- [ ] Confirm no regression in:
  - [ ] binding constraints
  - [ ] evidence / authority discipline
  - [ ] continuity truth

---

### 3. Narrator readability

- [ ] Review transition smoothness
- [ ] Review procedural vs natural prose feel
- [ ] Confirm narration preserves action clarity without flattening

---

## F. Validation method

- [ ] Use fixed high-signal scenarios:
  - [ ] `conflict_3char`
  - [ ] `arkham_multi_character_stress`
  - [ ] one lower-pressure conversational scenario
  - [ ] one long-session scenario

- [ ] Track structural metrics where useful:
  - [ ] override count
  - [ ] hard-route count
  - [ ] fairness count
  - [ ] attribution chain distribution

- [ ] Pair with qualitative judgment:
  - [ ] flow / handoff
  - [ ] progression naturalness
  - [ ] voice vitality
  - [ ] instruction drag
  - [ ] pressure integrity
  - [ ] scene readability

---

## G. Constraints

- [ ] No threshold tuning without repeated evidence
- [ ] No new subsystems
- [ ] No weakening of:
  - [ ] continuity authority
  - [ ] grounding / binding
  - [ ] evidence / authority discipline

---

## H. Exit criteria

- [ ] No obvious handoff / override / continuation instability in core scenarios
- [ ] Character prompts feel sharp without instruction drag regressions
- [ ] Narration remains readable and non-procedural
- [ ] Runtime quality is sufficient to defer further tuning until:
  - [ ] model change (e.g., Reasoner)
  - [ ] ingestion phase (Phase 3)

---