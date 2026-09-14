# Issue #201 — D-01-L Final Experimental Design & Consensus Refinement Report

**Date:** 2026-09-14  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** `investigating` — In Progress / Investigating / **P1**  
**Control substrate SHA:** `c751ea666f0cae6524698005aa5859721c2e9738`  
**Stage-3 decode synthesis SHA:** see §2 (this commit chain)  
**Prior records:** Stage-3 decode synthesis, locked Stage-3 scores, nomenclature map  
**Status:** D-01-L accepted **in principle** — execution **NOT authorized**

---

## 1. Exact current #201 state

| Field | Value |
|-------|-------|
| Issue state | OPEN / `investigating` |
| Project | In Progress / Investigating / **P1** |
| Stage-3 decode | **Accepted** |
| Plot / Storyteller classifications | **Accepted** |
| D-01-L | **Accepted in principle** — refinement complete; **execution NOT authorized** |
| D-10 | **Deferred** |
| EXP-3 complexity contrast | **Deferred** |
| Production redesign | **NOT authorized** |

---

## 2. Durable Stage-3 decode commit SHA

| Artifact | Path |
|----------|------|
| Locked Stage-3 sample means | `governance/records/issue201-stage3-governance-blind-scores-locked.json` |
| Stage-3 decode synthesis | `governance/records/issue-201-package-d-stage3-decode-synthesis-2026-09-14.md` |
| Stage-3 execution record (updated) | `governance/records/issue-201-package-d-stage3-preamble-decomposition-2026-09-14.md` |
| Issue body anchor staging | `governance/records/_issue-201-body-stage3-decode-update.md` |

**Scoring integrity:** Governance locked sample means **before** answer-key reveal. Per-dimension matrix remains Governance-held; not exported to repo at this step. Means in locked JSON are authoritative and unchanged.

**Commit SHA:** recorded at end of this step (§22).

---

## 3. Exact D-01-L causal question

> **Does Storyteller cognition produce material value over a multi-turn narrative trajectory when Plot cognition remains active?**

| Arm | Storyteller | Plot | Hook |
|-----|:-----------:|:----:|------|
| **Control** | ON | ON | none |
| **Ablated** | OFF | ON | `skipStorytellerCognition: true` |

All other relevant architecture matched (substrate SHA, scenarios, player-policy version, Plot resume lifecycle, continuity authority, PVR, director/character/narrator stacks).

---

## 4. Current Storyteller causal pathway (implementation evidence)

**Scope:** Documents what D-01-L actually tests under current code — not a redesign proposal.

### 4.1 Outputs produced (multi-turn path)

| Phase | Inference kinds | Product |
|-------|---------------|---------|
| **Preamble (per round)** | `storyteller_orientation`, `librarian_mediation` (storyteller lane), `storyteller_assessment` | `StorytellerAdvisoryPackage` bound to **current round** via `bindStorytellerAdvisoryPackage` |
| **Post-commit (per character commit, eligible)** | `storyteller_post_commit_issue_pressure` (+ optional contract correction) | Librarian proposal `issue_tension_pressure` → Continuity overlay mutation |

**Preamble block gated by `skipStorytellerCognition`** (`hg-round-orchestrator/service.mjs`). Post-commit issue-pressure path is **not** gated by that flag.

### 4.2 Persistence model

| Artifact | Persistence | Cross-turn? |
|----------|-------------|:-----------:|
| `StorytellerAdvisoryPackage` on `RoundFixture` | **Round-local** — new package each round when preamble runs | Per-turn regeneration informed by updated continuity |
| Plot cognition overlay (`plot_cognition_scope_id`) | **Session-persistent store** | **Yes** — both arms (Plot ON) |
| Continuity commits (`PublicEvent`, `IssueState`, history) | **Authoritative session state** | **Yes** — both arms |
| `issue_pressure_semantic_overlays` (S4) | **Continuity durable derived state** | **Yes** — when post-commit proposals apply |

**Key implication:** Storyteller does **not** carry forward a single advisory package across turns. Longitudinal value must manifest through (a) **per-turn fresh advisory** shaping Director/Character/Narrator decisions as continuity accumulates, and/or (b) **post-commit issue-pressure overlays** persisting in Continuity.

### 4.3 Downstream consumers (same turn)

Packaging mapper (`storyteller_packaging_mapper.py`) projects advisory slices into suggestive manifest lanes:

| Consumer | Categories consumed |
|----------|---------------------|
| **Director** | `narrative_priorities`, `active_tensions`, `progression_opportunities`, `unresolved_threads` |
| **Character** | `observations`, `active_tensions`, `progression_opportunities` |
| **Narrator** | `observations`, `active_tensions` (emphasis guidance) |

Available **before** director decision / character move / narrator presentation on that round.

### 4.4 Plot relationship

Plot cognition resume/init/update runs on **operative plot overlay + continuity** — **not** a direct consumer of `StorytellerAdvisoryPackage`. Interaction is **indirect**: both read committed history; Storyteller shapes same-turn director/character/narrator context; Plot shapes plot overlay and character advisory generation path.

### 4.5 Effects plausibly visible only on later turns

| Mechanism | Later-turn effect |
|-----------|-------------------|
| Director/character choices influenced by advisory | Alters **committed** events → changes future orientation inputs |
| `unresolved_threads` / `active_tensions` in advisory | Same-turn suggestive lanes; may bias choices that create continuity facts |
| `issue_tension_pressure` overlays | Eligibility/pressure semantics on **subsequent** rounds (#164) |
| Issue state escalation | ACTIVE/ESCALATING issues affect post-commit eligibility |

### 4.6 D-01-L interpretation flag

**`skipStorytellerCognition` removes preamble Storyteller only.** Residual `storyteller_post_commit_issue_pressure` may still execute on ablated arm (observed residual storyteller-kind counts on D-01b). D-01-L therefore primarily tests **preamble advisory longitudinal value**, with **partial post-commit pathway intact** on both arms.

If Governance requires pure preamble isolation, a separate gate would be needed to disable post-commit Storyteller proposer on ablated arm — **not proposed here** (would depart from D-01b hook parity). Document as **bounded interpretation confound**.

---

## 5. Arkham player-policy design (5-turn primary arc)

**Scenario:** `arkham_asylum_mess_hall_arena` — Harley, Ivy, Magpie; guards on margin.

**Policy version:** `arkham_d01l_policy_v1` (frozen before any arm executes).

### Turn 1 — Fixed entry (no branch)

| Field | Value |
|-------|-------|
| Objective | Establish Magpie's watch-focus and murmured provocation without open confrontation |
| Pressure | Social visibility; guard watch as object of attention |
| Prohibited knowledge | Magpie cannot know guard names, shift schedules, or off-screen authority decisions |
| Realization | *Locked Stage-3 stimulus:* murmur about gold watch while pushing food |

**Delayed-value opportunity #1:** Sets recruitment/alliance and guard-attention threads.

---

### Turn 2 — Refuse easy recruitment; test Ivy authority

| Field | Value |
|-------|-------|
| Objective | Decline table recruitment; force Ivy to show authority style |
| Pressure | Ivy/Harley recruitment pressure after Turn 1 reactions |
| Prohibited knowledge | No invented escape plans; no guard-internal procedures |

**Predicates** (evaluate on Turn 1 `presentation_text` only; first match wins):

| Priority | Predicate ID | Deterministic rule |
|----------|--------------|-------------------|
| 1 | `P2_IVY_DIRECT` | `/\b(Ivy|Poison Ivy)\b/i` matches AND `/\b(Magpie|Margaret|new (girl|leaf|bird))\b/i` matches |
| 2 | `P2_HARLEY_DOMINANT` | `/\bHarley\b/i` matches AND `/\b(Magpie|birdie|bird|sparkle)\b/i` matches AND NOT `P2_IVY_DIRECT` |
| 3 | `P2_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `P2_IVY_DIRECT` | `Magpie doesn't look away from the guard's watch. "I don't join tables on command. I watch who thinks they're invisible."` |
| `P2_HARLEY_DOMINANT` | `Magpie's mouth quirks. "Loud gets you noticed. I prefer knowing who notices back."` |
| `P2_DEFAULT` | `Magpie keeps her eyes on the gold at the margin. "Pretty things draw eyes. I'm counting whose."` |

**Delayed-value opportunity #2:** Alliance/recruitment pressure persists; authority test.

---

### Turn 3 — Escalate institutional visibility

| Field | Value |
|-------|-------|
| Objective | Increase guard-attention risk without physical action |
| Pressure | Consequence of prior social positioning |
| Prohibited knowledge | No reaching for watch; no violence |

**Predicates** (Turn 2 presentation):

| Priority | Predicate ID | Rule |
|----------|--------------|------|
| 1 | `P3_GUARD_ESCALATION` | `/\b(guard|watch|margin|sightline|log|paperwork|response)\b/i` |
| 2 | `P3_TABLE_PRESSURE` | `/\b(table|recruit|join|sit|bench)\b/i` |
| 3 | `P3_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `P3_GUARD_ESCALATION` | `Magpie murmurs, just carrying: "Wonder how many eyes it takes before even gold stops shining."` |
| `P3_TABLE_PRESSURE` | `Magpie pushes her tray an inch toward the center. "If you're selling belonging, price it where I can see the cost."` |
| `P3_DEFAULT` | `Magpie lets the silence sit, then: "Quiet rooms still have witnesses."` |

**Delayed-value opportunity #3:** Institutional pressure / environmental consequence thread.

---

### Turn 4 — Unresolved tension; refuse premature closure

| Field | Value |
|-------|-------|
| Objective | Hold thread open; resist NPC attempt to summarize or close Magpie's position |
| Pressure | Pecking-order consolidation |
| Prohibited knowledge | No confession; no alliance pledge |

**Predicates** (Turn 3 presentation):

| Priority | Predicate ID | Rule |
|----------|--------------|------|
| 1 | `P4_NAMED_THREAT` | `/\b(Magpie|Margaret)\b/i` AND `/\b(fool|stupid|mistake|log|write|reach)\b/i` |
| 2 | `P4_RECRUITMENT` | `/\b(join|table|interesting|worth|bird)\b/i` |
| 3 | `P4_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `P4_NAMED_THREAT` | `Magpie smiles without warmth. "Write what you like. I'll still be here when the ink dries."` |
| `P4_RECRUITMENT` | `Magpie taps her tray once. "I'm not shopping for family. I'm pricing the room."` |
| `P4_DEFAULT` | `Magpie finally looks up. "You all talk like lunch ends the story. It doesn't."` |

**Delayed-value opportunity #4:** Unresolved thread continuation vs premature resolution.

---

### Turn 5 — Delayed consequence beat

| Field | Value |
|-------|-------|
| Objective | Reference prior beats without resolving arc; test carryover |
| Pressure | Consequence of earlier social choices |
| Prohibited knowledge | No escape resolution; no guard confrontation outcome |

**Predicates** (Turn 4 presentation — cumulative tag):

| Priority | Predicate ID | Rule |
|----------|--------------|------|
| 1 | `P5_GUARD_THREAD` | any of turns 2–4 presentations matched `P3_GUARD_ESCALATION` OR `/\bguard\b/i` in Turn 4 |
| 2 | `P5_ALLIANCE_THREAD` | any of turns 2–4 matched `P2_IVY_DIRECT` or `P4_RECRUITMENT` |
| 3 | `P5_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `P5_GUARD_THREAD` | `Magpie glances toward the margin again. "Still shining. Still watching. Still not mine to reach for."` |
| `P5_ALLIANCE_THREAD` | `Magpie gathers her tray. "You wanted a shape from me. You got one. Don't mistake it for surrender."` |
| `P5_DEFAULT` | `Magpie stands slowly. "Same room tomorrow. Let's see what stuck."` |

**Delayed-value opportunity #5:** Delayed reaction / continuation without hard close.

---

## 6. Ayame player-policy design (3-turn confirmatory arc)

**Scenario:** `ayame_household_entry_evaluation` — Ayame, Kizzie applicant.

**Policy version:** `ayame_d01l_policy_v1` (frozen before execution).

### Turn 1 — Fixed entry

| Field | Value |
|-------|-------|
| Objective | Arrive; knock; begin interview threshold |
| Realization | *Locked Stage-3 stimulus:* double-check house number; knock |

**Delayed-value opportunity #1:** Household control agenda established.

---

### Turn 2 — Partial disclosure; test boundaries

| Field | Value |
|-------|-------|
| Objective | Answer one evaluative probe with deliberate partial truth |
| Pressure | Employment terms / household rules |
| Prohibited knowledge | No invented prior employment history beyond applicant card facts |

**Predicates** (Turn 1 presentation):

| Priority | Predicate ID | Rule |
|----------|--------------|------|
| 1 | `A2_FORMAL_CONTROL` | `/\b(interview|parlor|study|sitting room|terms|punctual|house)\b/i` |
| 2 | `A2_WARM_WELCOME` | `/\b(welcome|cold|come in|discuss)\b/i` AND NOT `A2_FORMAL_CONTROL` |
| 3 | `A2_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `A2_FORMAL_CONTROL` | `Kizzie meets her eyes. "I'm reliable. I don't blur lines between work and personal."` |
| `A2_WARM_WELCOME` | `Kizzie steps inside carefully. "I keep households orderly. I ask when I'm unsure."` |
| `A2_DEFAULT` | `Kizzie nods once. "I'm here about the live-in position. I'd rather hear expectations plainly."` |

**Delayed-value opportunity #2:** Interview progression / terms surfacing.

---

### Turn 3 — Terms asymmetry; consequence of prior answer

| Field | Value |
|-------|-------|
| Objective | Challenge or accept household boundary; leave decision open |
| Pressure | Persistent asymmetry (host/applicant) |
| Prohibited knowledge | No signed agreement; no access to private areas |

**Predicates** (Turn 2 presentation):

| Priority | Predicate ID | Rule |
|----------|--------------|------|
| 1 | `A3_RULES_STATED` | `/\b(rule|expect|standard|tolerate|otherwise|household)\b/i` |
| 2 | `A3_EVALUATIVE` | `/\b(reliable|orderly|carry|room|see how)\b/i` |
| 3 | `A3_DEFAULT` | else |

**Realizations:**

| Branch | Stimulus |
|--------|----------|
| `A3_RULES_STATED` | `Kizzie pauses at the threshold of the next room. "If curfew and privacy are fixed, say so now. I won't guess."` |
| `A3_EVALUATIVE` | `Kizzie folds her hands. "You wanted to see how I carry myself. Is there a rule you'd break for the right tenant?"` |
| `A3_DEFAULT` | `Kizzie waits. "I'd like to know what failure looks like here before I promise success."` |

**Delayed-value opportunity #3:** Continuation vs premature hire/reject resolution.

---

## 7. Deterministic branch-selection scheme

### Rules

1. **Policy frozen** as JSON artifact (`player_policy_v1.json`) hashed and recorded in tranche report before any live arm runs.
2. Branch selection uses **only** prior-turn `presentation_text` from the **same sequence** (same session).
3. **Predicate evaluation order:** ascending priority number; first true wins.
4. **No LLM** for player stimulus generation or branch choice.
5. **No access** to arm identity, Storyteller state, inference metadata, latency, tokens, or evaluator judgment.
6. Harness logs per turn: `{ turn, predicate_id, branch_id, realization_id, policy_hash }`.

### Predicate implementation

- Case-insensitive regex on presentation text (Unicode-normalized whitespace).
- Cumulative predicates (Turn 5 Arkham) read stored predicate hits from turns 2–4 log — not presentation re-parse alone.

### Leak prevention

Branch choice is a **function of observable NPC presentation**, which is a **legitimate downstream effect** of arm differences. Semantic intent is held constant by objective/pressure/prohibited-knowledge fields; realization varies only to maintain player coherence. This is **not** an architecture leak — it is the expected causal chain. Comparability is at **intent level**, not identical utterance level.

---

## 8. Causal-comparability analysis

| Risk | Mitigation |
|------|------------|
| Identical utterance misfit after divergent states | **Semantic player policy** with bounded realizations |
| Branch choice uses hidden state | Predicates on presentation text + logged cumulative tags only |
| Arm identity leaks into branch | Branch rules arm-agnostic; same policy object both arms |
| Plot starvation | Plot ON both arms; resume lifecycle identical |
| Continuity divergence | Same player intents; divergence is **outcome under test** |
| Post-commit Storyteller partial confound | Documented §4.6; both arms retain post-commit path |

**Primary comparability unit:** matched policy intent per turn within a sequence replication index (rep-1 control vs rep-1 ablated use same policy hash; rep-2 may use alternate policy variant only if both arms advance together — **single policy version for tranche**).

---

## 9. Information-preservation design

| Removed (ablated arm) | Preserved |
|-----------------------|-----------|
| Preamble Storyteller orientation/assessment | Scenario premise, PVR, continuity, Plot overlay, authoritative manifest path |
| Storyteller-mediated librarian (preamble lane) | Plot cognition, director/character/narrator authoritative inputs |
| Per-round advisory package | Legitimate committed history for both arms |

No authoritative state starvation. No synthetic Storyteller backfill on ablated arm.

---

## 10. Storyteller / Plot interaction handling

- **Plot ON both arms** — D-01b-equivalent ablation surface.
- Plot resume runs without Storyteller advisory binding (Stage-3 documented moderate interaction risk).
- **Accepted confound** for hook parity with Stage-3 D-01b.
- Sequence analysis records Plot inference kinds per turn; flag if ablated arm shows anomalous Plot kind absence.

---

## 11. Sequence-level primary rubric (blind)

Score **1–5** per dimension for the **complete sequence** (after reading all turns in order):

| # | Dimension |
|---|-----------|
| 1 | Thread persistence |
| 2 | Escalation coherence |
| 3 | Agenda persistence |
| 4 | Delayed consequences |
| 5 | Scene momentum |
| 6 | Cross-turn initiative |
| 7 | Reactive-loop avoidance |
| 8 | Premature-resolution avoidance |
| 9 | Plot-drift control |
| 10 | Cross-turn emotional/narrative continuity |

**Primary decision metric:** mean of sequence-level dimensions (unweighted unless Governance revises).

---

## 12. Per-turn secondary rubric

Retain locked **11 dimensions** per visible turn presentation (Stage-2/3 worksheet). Report **separately** — means per turn and per sequence. **Do not collapse** into primary endpoint.

---

## 13. Blind sequence-packet design

### Unit of evaluation

Anonymous **complete chronological sequence** (e.g., blind label `SEQ-A`).

### Packet contents (evaluator-facing)

1. Scenario briefing (Arkham or Ayame)
2. For each turn 1..N:
   - Player stimulus (realized text)
   - Visible presentation text
3. Sequence-level scoring grid
4. Optional per-turn scoring grid (secondary)

### Concealed

Arm, Storyteller on/off, experiment id, session id, case id, inference counts, latency, retry history, tokens, policy branch logs, predicate ids.

### Protocol

1. Governance (or designated evaluator) scores all sequences.
2. Lock sequence-level + per-turn scores.
3. Decode answer key.
4. Per-dimension detail remains Governance-held unless exported.

---

## 14. Correctness and state controls

### Per turn — automated harness capture

| Field | Purpose |
|-------|---------|
| `committed` | Semantic vs infra failure split |
| `pvr_validation_status` | Perception boundary |
| `domain_commit_id` | Continuity anchor |
| `continuity_turn_index` | Monotonicity |
| `selected_character_id` / actor routing | Director outcome |
| Plot kinds count / resume summary | Plot fairness |
| Storyteller preamble kinds (control >0; ablated =0) | Arm verification |
| Post-commit storyteller kinds | Confound monitor |
| `player_policy_branch` log | Branch audit |
| Wall time | Reliability bucket (exclude from quality) |
| `retry_count` / superseded attempts | Reliability |

### Per sequence

- All turns completed
- Same policy hash both arms for replication index
- No mid-sequence arm switch
- Continuity mutations logged (issue overlay changes if any)

### Failure classification

| Class | Action |
|-------|--------|
| Runtime/orchestration (`turn/end`, 0-byte, wall outlier) | Flag; exclude from quality if superseded; do not attribute to Storyteller |
| Semantic/boundary violation | Correctness failure; may invalidate sequence comparison |
| Incomplete sequence | Contamination — eligible for rep replacement per §15 |

---

## 15. Repetition strategy

### Initial bounded tranche (proposed — sufficient)

| Unit | Per arm |
|------|--------:|
| Arkham 5-turn sequences | **2** |
| Ayame 3-turn sequences | **2** |
| **Total sequences** | **8** (4 control, 4 ablated) |

**Rationale:** Matches Package D small-N discipline; 8 sequences × (5+3 avg turns) is substantial evaluator load; primary endpoint is sequence-level where n=2 per scenario per arm is consistent with Stage-2/3.

### Do NOT expand reps for variance reduction alone

### Additional sequences authorized only if

| Trigger | Example |
|---------|---------|
| Contradictory sequence-level outcomes | Control wins Arkham rep-1; ablated wins Arkham rep-2 with no correctness confound — Governance may authorize +1 rep/scenario/arm |
| Contaminated/incomplete sequence | Script turn skipped; noncommitted final turn |
| Intervention-specific correctness failure | PVR invalid attributable to ablation hook misconfiguration |
| Extreme path divergence destroying intent match | Branch log shows default branch 4/5 turns because presentations empty/corrupt |

**Max expansion without new Governance gate:** +1 sequence per scenario per arm (would become 3+3 per arm).

---

## 16. Retry / failure handling

- Same as Stage-3: per-turn retry supersession allowed; **committed presentation** enters packet.
- Failed superseded attempts excluded from blind packets.
- Wall-time outliers flagged; semantic scores retained but analytically separated.
- If sequence cannot complete after 2 full-sequence attempts → mark `sequence_contaminated`; eligible for replacement rep, not unbounded retry.

---

## 17. Prospective interpretation rules (pre-registered, qualitative)

Small-N qualitative rules — **not** p-values.

### A. Storyteller demonstrated longitudinal value

Control sequences show **meaningful advantage** on **≥6/10** sequence dimensions in **both** Arkham reps **or** in Arkham aggregate **and** at least neutral on correctness. Ayame not contradictory.

### B. Storyteller lacks demonstrated longitudinal value

Ablated sequences **comparable** on sequence dimensions (≤0.15 mean delta per scenario, descriptive) **and** correctness comparable, while preamble Storyteller kinds removed.

### C. Delayed but not per-turn value

Per-turn means within **≤0.10** per scenario; sequence-level advantage **≥0.20** for control on **≥4** trajectory dimensions.

### D. Scenario / complexity conditioned

Arkham and Ayame sequence deltas diverge by **≥0.20** with coherent correctness story (e.g., stress shows value; controlled does not).

### E. Movable off critical path

Sequence-level or objective issue-pressure deltas present; per-turn prose neutral; post-commit kinds differ — supports periodic/async hypothesis **without** proving worthless function.

### F. Inconclusive

Contradictory reps, contamination, or correctness confounds dominate → **no placement decision**; Governance chooses rep extension or redesign.

**Thresholds are descriptive guides** — Governance adjudicates final classification.

---

## 18. Synchronous-placement inference limits

| Question | D-01-L can establish | D-01-L cannot establish |
|----------|---------------------|-------------------------|
| Every-turn synchronous preamble | Whether sync preamble adds **multi-turn** value | Optimal frequency (every turn vs every N) |
| Conditional invocation | Complexity-conditioned signal (Arkham vs Ayame) | Exact gate thresholds |
| Periodic / between-scene | Whether value is arc-level not line-level | Best schedule |
| Post-presentation async | Post-commit pathway differential (partial) | Full async architecture design |
| Precomputed trajectory | — | Any offline precomputation design |

**Positive longitudinal result** → does **not** auto-justify current synchronous placement.  
**Null result** → does **not** prove all Storyteller functions worthless (post-commit + future horizons remain).

---

## 19. Expected architectural-work delta

| Metric | Control vs ablated (per turn, indicative from Stage-3) |
|--------|--------------------------------------------------------|
| Preamble Storyteller kinds | −2 to −3 per turn |
| Storyteller-mediated librarian | −1 to −6 per turn (noisy) |
| Plot kinds | **0** (both ON) |
| Post-commit storyteller kinds | **≈0 delta** (confound) |
| Inference count per turn | −5 to −15 (scenario-dependent) |

**5-turn Arkham sequence (ablated):** roughly **25–75** fewer preamble-related inferences vs control (order-of-magnitude; not a quality metric).

---

## 20. Expected information gain

| Question | Gain |
|----------|------|
| Multi-turn Storyteller value with Plot ON | **High** — primary gate |
| Preamble vs post-commit contribution | **Medium** — partial confound remains |
| Line vs arc value | **Medium** — dual rubric |
| Scenario conditioning | **Medium** |
| Sync placement justification | **Low–Medium** |
| D-10 authorization | **Low** — still deferred |

---

## 21. Remaining confounds

1. Post-commit Storyteller on ablated arm (§4.6)
2. Storyteller↔Plot indirect interaction
3. Fixed policy ecological validity
4. Small-N (2 seq/scenario/arm)
5. Predicate regex brittleness
6. Evaluator fatigue on long packets
7. Infrastructure instability class (Stage-3)
8. Arm-correlated presentation → branch correlation (accepted causal structure)

---

## 22. Artifact / Issue-anchor disposition

| Artifact | Disposition |
|----------|-------------|
| Stage-3 locked scores JSON | **Commit** (this step) |
| Stage-3 decode synthesis | **Commit** (this step) |
| D-01-L refinement (this doc) | **Commit** (this step) |
| `player_policy_v1.json` | **Not created** — execution gate |
| D-01-L harness | **Not created** — execution gate |
| Issue body anchor | Update to synthesis + refinement SHAs |

---

## 23. Governance decisions required for execution authorization

1. **Accept D-01-L refined design** — semantic player policy, sequence-primary rubric, blind whole-sequence packets?
2. **Authorize execution** of D-01-L tranche (8 sequences; 2 Arkham + 2 Ayame per arm)?
3. **Accept post-commit Storyteller confound** — or require extended hook disabling post-commit on ablated arm (departs from D-01b parity)?
4. **Freeze player policies** — approve `arkham_d01l_policy_v1` and `ayame_d01l_policy_v1` text as specified?
5. **Authorize blind evaluator** — Governance scoring with sequence-primary endpoint?
6. **Confirm rep expansion triggers** (§15) — no ad-hoc rep increase?
7. **Defer D-10 and EXP-3** — unchanged?
8. **Export Stage-3 per-dimension matrix** to repo (optional)?

---

## Session boundary

**Status:** `investigating` — In Progress / Investigating / P1  
**Completed:** Stage-3 durable commit; D-01-L consensus refinement  
**Not executed:** D-01-L harness, live runs, D-10, EXP-3, production changes
