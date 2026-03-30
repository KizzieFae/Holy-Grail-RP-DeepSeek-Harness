# Resolved Outcome System — Scene Validation Plan

**Goal:**  
Validate real-scene behavior of the registry-backed resolved outcome system under natural conditions.

**Scope:**  
- `lodging.sleep_surface`
- `communication.housing_call`
- `medical.suppressant_formulation`
- `access.location_entry`

**Method:**  
Run targeted scenes → audit with dual-layer pipeline → record results → do not modify system mid-run.

---

## General Rules

- [ ] Do NOT change prompts, schema, or code during a scene run
- [ ] Use the full audit pipeline (Narrative + Resolved Outcome)
- [ ] Record all findings before making any adjustments
- [ ] Prefer multiple short scenes over one long debugging session

---

# Scene Set

## 1. Calm / Low-Pressure Scene

**Purpose:** Validate low false positives

**Setup:**
- Minimal conflict
- Casual dialogue
- Light movement / interaction

**Checklist:**
- [ ] No emissions occur without explicit settlement language
- [ ] Ambiguous or casual phrasing does NOT trigger emissions
- [ ] Grounding remains minimal and accurate
- [ ] No false positives in any aspect

---

## 2. High-Conflict / Multi-Speaker Scene

**Purpose:** Validate supersession and contradiction handling

**Setup:**
- 2–3 characters
- Conflicting authority or decisions
- Rapid back-and-forth dialogue

**Checklist:**
- [ ] Conflicting rulings produce correct supersession
- [ ] Only one active value exists per slot
- [ ] No duplicate active states
- [ ] Grounding reflects the latest active state only
- [ ] Prior states are properly superseded

---

## 3. Control-Language / Ambiguity Stress Scene

**Purpose:** Validate ambiguity guard rules

**Include phrases like:**
- "wait"
- "not yet"
- "stay here"
- "for now"
- "until I say otherwise"

**Checklist:**
- [ ] No emissions triggered by control language alone
- [ ] No accidental promotion from ambiguous phrasing
- [ ] All such turns classify as `Correct non-emission`
- [ ] No grounding facts created from control-only language

---

## 4. Mixed Clarity Scene

**Purpose:** Validate selective emission behavior

**Include:**
- One clear permission/assignment
- One ambiguous restriction
- One invalid location or value

**Checklist:**
- [ ] Only explicit, valid settlement produces emission
- [ ] Ambiguous statements do NOT emit
- [ ] Invalid values are NOT remapped
- [ ] Invalid emissions are rejected (e.g., `invalid_location_id`)
- [ ] Grounding reflects only valid promoted outcomes

---

## 5. Long Scene (10–20 Turns)

**Purpose:** Validate stability over time

**Setup:**
- Natural scene progression
- Multiple interactions across turns

**Checklist:**
- [ ] No drift in slot state over time
- [ ] No loss of previously established state
- [ ] Supersession remains correct across turns
- [ ] No duplicate or conflicting active slot values
- [ ] Grounding remains synchronized with active state throughout

---

# Per-Scene Audit Checklist

For each scene:

## Emission Accuracy
- [ ] All expected emissions occurred
- [ ] No missed emissions
- [ ] No false positives
- [ ] Ambiguous cases correctly classified as non-emission

## Promotion Behavior
- [ ] All valid candidates promoted correctly
- [ ] No incorrect promotions
- [ ] No incorrect rejections
- [ ] Identical-value no-ops handled correctly

## Slot Integrity
- [ ] No duplicate active states per slot
- [ ] No cross-subject leakage
- [ ] No subject/resource slot confusion
- [ ] Supersession behavior is correct

## Grounding Consistency
- [ ] Grounding matches active slot state
- [ ] No stale facts after supersession
- [ ] No missing facts after valid promotion
- [ ] No grounding from rejected/invalid outcomes

---

# Completion Criteria

All conditions must be met:

- [ ] Near-zero false positives across all scenes
- [ ] Near-zero missed emissions across all scenes
- [ ] 100% correct promotion behavior
- [ ] 100% slot integrity (no duplicates, no leakage)
- [ ] 100% grounding consistency

---

# Exit Condition

When all completion criteria are satisfied:

- [ ] Mark validation phase as complete
- [ ] Freeze current system behavior as baseline
- [ ] Proceed to next phase (memory, advisory, or expansion)

---