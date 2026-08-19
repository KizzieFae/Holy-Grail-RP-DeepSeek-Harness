# Issue #251 — Arm B physical/perceptual severance doctrine (planning draft)

**Status:** Implementation spec for Arm B (`physical_severance_v1`). **Not** production default. **Not** `validated`.

**Parent investigation:** [Issue #251](https://github.com/KizzieFae/Holy_Grail_RP/issues/251)

**Related artifact:** [i251_doctrine_isolation_phase1_plan.json](./i251_doctrine_isolation_phase1_plan.json)

**Lane separation (unchanged):**

| Lane | Owner |
|------|-------|
| Continuity authority | #224 — committed state > audit |
| Observational evaluation | #243 — `evaluate_case`, `ambiguous_threshold` |
| Adjudication posture | #246 — observational only |
| Structural / ingress | #249 |
| Retry flatten | #250 |
| Exit ontology / missed emission | #251 |

---

## A. Purpose / rationale

### Why hybrid Arm A is insufficient

Source-of-truth verification (2026-05-25) established that successful #251 treatment runs **correctly injected** topology `v1_next7_issue251_awareness_clean` with clean preflight (no prompt-byte regression). The tested bundle nevertheless combines:

1. **Three-line severance** (“materially leaves the shared live scene”)
2. **Four-factor shared-awareness exit teaching** (all four required in same beat window)
3. **Explicit social-tether / temporary-task negatives** (doorway reply, temporary-task framing alone, margin/doorway tether gate)

These are **different completion criteria** coexisting in one prompt. The model receives simultaneous positive shut-door examples and negatives that block exit when threshold speech or temporary framing is present — even when physical severance completes in the same beat.

Existing matrix evidence (`i251_exit_stability_matrix_adjudicated.json`, n=32) therefore validates **hybrid shared-awareness severance doctrine only**. It does **not** validate an intended physical/perceptual-severance-decisive doctrine, which was discussed in orchestration but **never codified or isolated**.

### Why GM3 remains unresolved

**GM3** (`session_912` R1T12) is the primary anchor seam. Under Arm A (hybrid):

| Source | Result |
|--------|--------|
| Anchor matrix treatment (N=3) | 1/3 S1 pass |
| Min-clarification AB (N=10) | 3/10 S1 pass |
| Broad matrix (n=1) | `no_covered_change`; adjudicated `ambiguous_threshold` |
| Production exact replay | **Not treatment evidence** — uses production prompt |

GM3 beats simultaneously match Arm A **positive** (traverse out, shut door, lose audibility) and **negative** (doorway reply, “ten minutes” temporary framing, threshold linger) teaching. Stochastic instability (1/3 → 3/10) under **clean** preflight is best explained by **internal doctrinal conflict**, not harness failure.

### Why doctrine isolation is required

To answer whether physical/perceptual severance completion should be decisive for `off_focal`, Arm B must be:

- **Textually isolated** — no four-factor awareness block, no shared-awareness continuity axis, no temporary-task/doorway-tether gates that contradict physical completion
- **Harness-isolated** — separate topology, markers, override function, contamination preflight
- **Evaluated in parallel** — same frozen audits under Arm A and Arm B with three-layer reporting (L1/L2/L3)

Without isolation, threshold-exit conclusions remain **partially contaminated** by hybrid doctrine overlap.

---

## B. Arm definitions

### Arm A — Hybrid shared-awareness severance (existing)

| Field | Value |
|-------|-------|
| **Name** | Hybrid awareness-clean |
| **Topology** | `v1_next7_issue251_awareness_clean` |
| **Env** | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_issue251_awareness_clean` |
| **Status** | Implemented; evidence collected |
| **Override function** | `apply_issue251_awareness_clean_prompt_overrides()` |
| **Doctrine schema** | `hybrid_awareness_v1` |
| **Primary completion criterion** | All four shared-awareness factors + severance lines |
| **Evidence era label** | `doctrine_era: hybrid_awareness_v1` |

**Markers (Arm A — required when active):**

- `participation_awareness_clean_isolation_v251`
- `participation_awareness_doctrine_issue251_v1`
- `participation_severance_doctrine_issue251_canonical_v1`

### Arm B — Physical/perceptual severance (spec only)

| Field | Value |
|-------|-------|
| **Name** | Physical/perceptual severance clean |
| **Topology** | `v1_next7_issue251_physical_severance_v1` |
| **Env** | `RP_ISSUE240_PROMPT_TOPOLOGY=v1_next7_issue251_physical_severance_v1` (future) |
| **Status** | **Planning draft only — not implemented** |
| **Override function** | `apply_issue251_physical_severance_prompt_overrides()` (proposed) |
| **Doctrine schema** | `physical_severance_v1` |
| **Primary completion criterion** | Physical exit from shared scene interaction space **and** natural audibility/visibility of live exchange ends |
| **Evidence era label** | `doctrine_era: physical_severance_v1` |

**Markers (Arm B — required when active):**

- `participation_physical_severance_isolation_v251`
- `participation_physical_severance_doctrine_issue251_v1`

**Shared across both arms:**

- #249 proposal-schema teaching (`proposal_schema_teaching_v249_a`)
- Margin/deepen/reverse ontology **suppressed**
- Rejected continuity-preservation sentence **absent**
- Frozen-audit replay harness path (no live turn_runner chat accumulation)

---

## C. Final proposed Arm B doctrine text

> **Implementation note:** The blocks below are the authoritative spec for future `prompt_topology_issue240.py` builders. Wording is final for planning consensus; minor editorial tightening allowed at implementation without semantic change.

### C.1 Opening block

**Function (proposed):** `build_issue251_physical_severance_clean_opening(char_name)`

**Marker:** `participation_physical_severance_isolation_v251`

```text
You are {char_name}, taking your next turn in an ongoing roleplay scene.

Act primarily as this character: voice, pressure, subtext, and in-character judgment come first. Every beat also requires an explicit root ``semantic_evaluation`` judgment (see trigger-adjacent self-report below and OUTPUT RULES).

Do not emit root ``semantic_proposals`` or empty proposal arrays.

participation_physical_severance_isolation_v251 — margin/deepen/reverse participation ontology suppressed; physical/perceptual severance exit doctrine active (investigation topology; not production default).
```

### C.2 Semantic self-report block

**Function (proposed):** `build_issue251_physical_severance_semantic_block(char_name)`

Uses standard header: `FOR THIS BEAT — SEMANTIC SELF-REPORT`

```text
FOR THIS BEAT — SEMANTIC SELF-REPORT (same move you are authoring):

Root ``semantic_evaluation`` required every beat.
- ``decision``: ``covered_change`` or ``no_covered_change``
- ``proposals``: non-empty array only when ``decision`` is ``covered_change``; omit when ``no_covered_change``

Proposal schema — allowed keys ONLY: ``kind``, ``character``, optional ``operation`` (``excursion_lifecycle`` only).
- ``kind``: ``off_focal`` | ``reentry`` | ``excursion_lifecycle``
- ``character``: your acting character runtime id (non-empty)
- ``operation``: ``open`` | ``update`` | ``close`` — required for ``excursion_lifecycle``; forbidden for ``off_focal`` and ``reentry``

{proposal_schema_teaching_v249_a marker block — unchanged from v1_next7}

Forbidden on proposals: ``reason``, ``description``, ``rationale``, ``strategy``, ``subject``, ``character_id``, or any other key.

Examples (use your character id instead of ACTOR_ID):
{"decision":"covered_change","proposals":[{"kind":"off_focal","character":"{actor_id}"}]}
{"decision":"covered_change","proposals":[{"kind":"reentry","character":"{actor_id}"}]}
{"decision":"no_covered_change"}

``covered_change`` with ``off_focal`` only when this beat completes physical/perceptual severance (see doctrine block below). If severance has not completed in this beat, use ``no_covered_change``.

Do not emit root ``semantic_proposals`` or ``semantic_proposals: []``.

{build_issue251_physical_severance_doctrine_block()}

Do not explain this analysis in dialogue or action beats.
```

### C.3 Doctrine block

**Function (proposed):** `build_issue251_physical_severance_doctrine_block()`

**Marker:** `participation_physical_severance_doctrine_issue251_v1`

```text
Participation exit doctrine (participation_physical_severance_doctrine_issue251_v1 — do not recite in dialogue):

``off_focal`` when **this beat completes physical/perceptual severance** from the shared live scene:

(1) you leave the shared scene interaction space (not in-room repositioning or margin-only movement), **and**
(2) the live exchange is no longer naturally audible/visible between those who remain and you (perceptual severance).

**Completion rule:** judge severance by how the beat **ends**, not by interim threshold talk. Doorway speech, timers, or “back soon” framing during an exit arc do **not** prevent ``off_focal`` if the beat ends with completed physical/perceptual severance.

**Emotional or social withdrawal** while still present in the shared live scene is not ``off_focal``.

A withdrawal arc may begin gradually across earlier beats, but the moment physical/perceptual severance completes is itself a new participation transition.

**NOT ``off_focal``:**
- in-room bunk/couch/logistics without leaving the shared scene interaction space;
- same-beat return before severance completes;
- remote contact that keeps the live exchange naturally audible/visible;
- adjacent space where the exchange remains naturally audible/visible;
- beat ends still inside the shared scene interaction space (threshold linger without crossing).

**Canonical positive (completed severance):**
traverse out of the room and shut the door (or equivalent boundary) so the live exchange is no longer naturally audible/visible → ``covered_change`` with ``off_focal``.

**Canonical negative (severance not completed):**
beat ends with character still inside the room, or still naturally audible/visible to those remaining without completed boundary crossing → ``no_covered_change``.
```

### C.4 Explicit completion criteria (summary)

| Criterion | Arm B rule |
|-----------|------------|
| Spatial | Must leave shared scene interaction space (not in-room reposition) |
| Perceptual | Live exchange no longer naturally audible/visible at beat end |
| Communicative | **Not** a separate gate — folded into perceptual test |
| Awareness continuity | **Not required** — no “track live exchange together” test |
| Temporary-task framing | **Does not block** exit if severance completes in-beat |
| Doorway/threshold speech | **Does not block** exit if beat ends with completed severance |
| Emotional withdrawal alone | **Not** exit |
| Same-beat return | **Not** exit if severance never completed |

### C.5 Positive examples (teaching)

1. **Shut-door exit:** Character traverses out, shuts door; exchange no longer audible/visible → `covered_change` + `off_focal`.
2. **Temporary errand with completion:** “Five minutes” said at threshold, then character exits and door closes; no longer audible → `off_focal` (temporary framing irrelevant once severance completes).
3. **Quiet practical departure:** Character leaves shared space with perceptual severance, minimal dialogue → `off_focal`.

### C.6 Negative examples (teaching)

1. **In-room withdrawal:** Character disengages emotionally but remains in shared scene → `no_covered_change`.
2. **Threshold linger without crossing:** Character pauses at door, beat ends still in doorway audible to room → `no_covered_change`.
3. **Same-beat return:** Character steps out then re-enters before severance completes → `no_covered_change`.
4. **Remote phone tether:** Call keeps exchange live across distance → `no_covered_change`.
5. **Adjacent audible room:** Character in adjoining space still naturally heard → `no_covered_change`.

---

## D. Contamination-prevention requirements

Arm B preflight must **fail closed** if any forbidden content is present or any required marker is absent.

### D.1 Required markers (Arm B)

| Marker | Purpose |
|--------|---------|
| `participation_physical_severance_isolation_v251` | Topology isolation tag |
| `participation_physical_severance_doctrine_issue251_v1` | Doctrine block tag |
| `proposal_schema_teaching_v249_a` | #249 schema teaching (shared) |

### D.2 Forbidden markers (Arm B — must be absent)

| Marker / string | Reason |
|-----------------|--------|
| `participation_awareness_doctrine_issue251_v1` | Arm A four-factor block |
| `participation_awareness_clean_isolation_v251` | Arm A topology tag |
| `participation_severance_doctrine_issue251_canonical_v1` | Arm A severance wrapper (optional: may allow if text is subset — prefer separate Arm B block only) |
| `participation_severance_clarification_issue251_v1_min` | Pre-commit hybrid-era header |

### D.3 Forbidden phrases (Arm B — must be absent)

| Phrase | Reason |
|--------|--------|
| `all four` | Four-factor awareness gate |
| `shared-awareness continuity` | Arm A primary teaching axis |
| `shared scene awareness continuity ends` | Awareness factor (4) |
| `no longer participate in the live exchange` as separate gate | Communicative severance as standalone factor |
| `temporary-task framing alone` | Arm A negative that blocks GM3-class exits |
| `physical displacement alone` | Arm A negative contradicting Arm B completion rule |
| `doorway tether` | Arm A semantic gate |
| `Margin, doorway tether, or temporary-task framing without shared-awareness severance` | Arm A semantic gate (full sentence) |
| `continue/deepen/reverse` | Margin ontology |
| `partially withdrawn` | Margin ontology capsule |
| `margin withdrawal/rejoin` | Margin ontology |
| Fuzzy threshold calibration strings | Pre-#251 contamination |
| Rejected continuity-preservation sentence | Tested and rejected under hybrid |

### D.4 Arm A cross-contamination checks (when running dual-arm)

Arm A preflight must **not** contain Arm B markers:

- `participation_physical_severance_isolation_v251`
- `participation_physical_severance_doctrine_issue251_v1`

### D.5 Preflight assertions (both arms)

Every replay sample must record:

```yaml
preflight:
  doctrine_arm: A | B
  doctrine_schema_version: hybrid_awareness_v1 | physical_severance_v1
  topology_inferred: ...
  contamination_hits: []          # must be empty to include in semantic rates
  contamination_clean: true       # required for cohort analysis
  required_markers_present: true
  forbidden_markers_absent: true
  prompt_sha256: ...
```

Samples with `contamination_clean: false` are **excluded** from doctrine comparison numerators and flagged for harness debugging.

---

## E. GM3 interpretation section

**Case:** `EXIT-C-GM3` — `session_912` R1T12 — Willow Reeves staged temporary departure (garage bay / window latch; doorway reply; door shut).

**Historical production decision:** `no_covered_change`

### Expected behavior under Arm A (hybrid)

| Dimension | Expectation |
|-----------|-------------|
| **Doctrine tension** | High — beat matches shut-door positive AND doorway/temporary-task negatives |
| **Stochastic S1** | Low/intermittent pass (observed 1/3–3/10 under clean preflight) |
| **Typical model decision** | `no_covered_change` when model weights threshold speech / temporary framing |
| **L2 adjudicated** | Often `ambiguous_threshold` when `no_covered_change` + `exec_depart` fiction signals |
| **Interpretation** | Ambiguity is **expected** under hybrid doctrine — not a harness defect |

### Expected behavior under Arm B (physical/perceptual)

| Dimension | Expectation |
|-----------|-------------|
| **Doctrine tension** | Low — temporary framing explicitly non-blocking if severance completes |
| **Stochastic S1 (hypothesis)** | Higher pass rate if model follows completion-at-beat-end rule |
| **Expected label (L3)** | `covered_change` + `off_focal` when replay beats end with door shut and perceptual severance |
| **L2 adjudicated** | May still show `ambiguous_threshold` (#243 unchanged) — **L3 divergence is diagnostic** |
| **Interpretation** | GM3 is the **primary discriminator** — if Arm B S1 pass ≥70% at N=10 with clean preflight and Arm A remains ~30%, physical/perceptual doctrine resolves the hybrid conflict |

### Why GM3 is the primary discriminator

1. Only anchor case with **clean treatment preflight** and **persistent stochastic failure** under Arm A.
2. Beat fiction shows **completed departure cues** (`exec_depart: true`) — aligns with Arm B, conflicts with Arm A negatives.
3. Same frozen audit enables **paired A/B comparison** without confounds.
4. Broad matrix + AB matrix + anchor matrix all converge on GM3 as the narrowed seam.

---

## F. Evaluation methodology summary

Three layers required for all Phase 1 reruns. **Do not collapse layers.**

### L1 — Deterministic (#251 / #249 structural)

Source: `i251_metrics.py` on first attempt.

| Field | Use |
|-------|-----|
| `S1_semantic_intent_correct` | Primary intent vs expected label |
| `S2_structural_legality_pass` | Gate for clean semantic reads |
| `issue251_genuine_miss` | S1 fail + S2 pass → #251 lane |
| `route_to_249` | S1 pass + S2 fail → #249 lane |
| `decision`, `proposal_kinds` | Raw emission |

**Clean S1 rate:** filter `S2_structural_legality_pass == true` only.

### L2 — Adjudicated (#243-B observational)

Source: `i251_replay_adjudication.py` → `evaluate_case` + dorm boundary signals.

| Field | Use |
|-------|-----|
| `adjudicated_semantically_correct` | Observational semantic alignment |
| `ambiguous_or_recoverable` | Threshold cases — first-class, not failure |
| `semantic_eval_judgment.corrected_category` | e.g. `ambiguous_threshold` |
| `boundary_signals` | Fiction-side departure cues |

**Posture:** Observational (#246). Does **not** override #224 continuity authority.

### L3 — Doctrine-alignment (#251 doctrine-specific, new)

Source: proposed adapter extension keyed to `doctrine_arm`.

| Field | Use |
|-------|-----|
| `expected_under_arm` | Rubric label for active arm |
| `doctrine_aligned` | Replay matches arm-specific completion criteria |
| `rationale` | Beat-end severance analysis under arm rubric |

**Purpose:** Detect when L2 (`ambiguous_threshold`) conflicts with Arm B completion rule. L3 is authoritative for **doctrine isolation experiment** conclusions; L2 remains for cross-era #243 comparison.

---

## G. Non-goals / constraints

| Constraint | Status |
|------------|--------|
| Production prompt merge | **Not in scope** — investigation topology only |
| #243 evaluator rewrite | **Explicitly out of scope** |
| #224 continuity authority | **Unchanged** — replay observational |
| #249 schema teaching | **Shared** — both arms retain proposal-schema teaching |
| #250 retry flatten | **Out of scope** — first-attempt only |
| Live turn_runner activation | **Not in scope** — frozen-audit replay path |
| Issue #251 GitHub mutation | **Deferred** — spec review first |
| Adjudication adapter implementation | **Deferred** — L3 spec only in this document |
| Remote/phone cohort (P03) | **Excluded** from Phase 1 — edge case per existing plan |

---

## H. Success criteria

Phase 1 Arm B evidence is **successful** if **all** of the following hold:

### H.1 Isolation integrity

- [ ] 100% of Arm B samples pass contamination preflight (zero forbidden markers/phrases)
- [ ] 100% of Arm A samples pass existing hybrid preflight
- [ ] No cross-arm marker leakage in any sample

### H.2 GM3 discriminator (N=10 per arm)

- [ ] Arm B S2-clean S1 pass rate **≥ 70%** (≥7/10)
- [ ] Arm B L3 doctrine-alignment pass rate **≥ 70%**
- [ ] Arm A S2-clean S1 pass rate **≤ 40%** (confirms hybrid conflict baseline) OR Arm B exceeds Arm A by **≥ 40 percentage points**

### H.3 Exit cohort stability (C + D categories, N=3 per arm)

- [ ] Arm B S2-clean S1 pass rate on exit cases **≥ 50%** (4/8 minimum)
- [ ] Arm B does not regress explicit exit controls (A + B categories): **≥ 2/3** pass on 908-P01, 900-T3, 910-R5T3 each

### H.4 Guard stability (non-exit, N=3 per arm)

- [ ] Arm B false-positive `off_focal` rate on guard cases **≤ 1/15** samples (≤1 FP across P02, P05, P04, CTRL-GM2, 911-P01 × 3)
- [ ] No guard case shows **Arm B FP while Arm A correct** pattern ≥2 times (regression signal)

### H.5 Evidence sufficiency for Phase 2 decision

- [ ] A vs B delta documented per case with L1/L2/L3
- [ ] If success criteria met → authorize Phase 2 full n=32 dual-arm rerun
- [ ] If GM3 criteria fail → Arm B doctrine revision before any implementation merge; **do not** promote to canon

**Failure** of Arm B success criteria does **not** invalidate Arm A hybrid evidence — it means physical/perceptual doctrine does not resolve the seam under tested wording.

---

## Appendix — Arm A vs Arm B delta (quick reference)

| Element | Arm A (hybrid) | Arm B (physical/perceptual) |
|---------|----------------|------------------------------|
| Primary axis | Shared-awareness continuity | Physical/perceptual severance completion |
| Exit gate | All four factors | Two factors: spatial departure + perceptual severance at beat end |
| Temporary-task framing | Blocks exit alone | Does not block if severance completes |
| Doorway speech | Blocks if others still hear | Allowed if beat ends with severance |
| Awareness continuity tracking | Required | Not required |
| Semantic gate | Margin/doorway tether/temporary-task without awareness severance | Severance not completed in beat |

---

**Document version:** `physical_severance_doctrine_draft.v1`  
**Authoring date:** 2026-05-25  
**Next gate:** Spec review / consensus before any `prompt_topology_issue240.py` implementation
