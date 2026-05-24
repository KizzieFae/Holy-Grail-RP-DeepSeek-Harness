# Manual Adjudication Packet — Selective Cohesion Failures

**Scope:** Read-only presentation of suspected audit/extraction failures from sessions **899–907**.  
**No classifications were changed.** This packet supports human semantic review only.

**Artifact paths referenced:**
- Extractions: `validation_runs/willow_departure_*_v1.jsonl`, `validation_runs/cohesion_slate/*.jsonl`
- Comparisons: `validation_runs/cohesion_slate/*_comparison.json`, `validation_runs/willow_departure_experiment_comparison.json`
- Audits: `rp_app/data/rp_audits/session_{899..907}/`
- Prior reports: `validation_runs/anchor_only_must_remain_experiment_validation_report.md`, `validation_runs/broad_validation_slate_anchor_cohesion_report.md`

---

## 1. System understanding report

### What the automated layer is doing

- **Probe harness** forces actor-targeted Traveler triggers (clean withdrawal, doorway continuation, relocation, rebound, disengaged).
- **Extraction rubric** compares `expected_rubric` (from manifest) vs model `semantic_evaluation` + committed roster.
- **C3 (`missed_covered_change`)** = probe expected a participation shift (`covered_change`) but model reported `no_covered_change` and/or no accepted `off_focal` commit.
- **C1 on threshold probes** = expected no roster shift; still flagged **`F_fiction_roster_drift`** when exit fiction coexists with onstage roster.

### Why manual review matters (per user / session_890 context)

Prior Omega Student review showed audit false positives when:

- dorm geometry is a **single room + threshold**, not a hard exit;
- actors remain **conversationally reachable** through an open door;
- **partial exits** (doorframe, hall just outside) carry social continuity;
- large scenes allow **table-to-table** or **margin repositioning** without true scene departure.

**Arkham cafeteria** is the critical new topology: actors can leave a **focal table exchange** while remaining **inside the mess hall**, **visually observing**, and **audibly reachable across the room**. Automated `off_focal` may conflate:

- *social withdrawal from current thread* vs
- *physical/scene exit*.

### Session map

| Session | Arm | Archetype |
|---------|-----|-----------|
| 899 | Willow baseline (all `must_remain`) | Dorm / mobility reference |
| 900 | Willow selective flex | *(no C3 on first actor — omitted)* |
| 901 | Both alphas flex | Dorm regression arm |
| 902 | Household baseline | Ensemble guard |
| 903 | Household selective flex | Ensemble guard |
| 904 | Arkham baseline | 6-char cafeteria |
| 905 | Arkham selective flex | 6-char cafeteria |
| 906 | Apartment baseline | Slow-burn dyad |
| 907 | Apartment selective flex | Slow-burn dyad |

**Total first-actor C3 rows extracted:** 20 (see Appendix A).

---

## 2. Suspected false positives

*Cases where automated “failure” or `off_focal` success may **not** match dramatic/social reality.*

---

### Case FP-1 — Selina P06 baseline `off_focal` may be over-commit (session 904)

**Metadata**
| Field | Value |
|-------|-------|
| Session | **904** |
| Probe | **P06** — witness soft withdrawal |
| Archetype | Arkham cafeteria |
| Actor | Selina Kyle |
| Arm | Baseline |
| Classification | **C2** (classified as *success*, but suspect **false positive commit**) |
| Why flagged for review | Same trigger as 905; baseline emitted `off_focal` and removed Selina from `present_characters` despite prose describing **in-room margin repositioning**. |

**Traveler trigger**
> Traveler: Selina, withdraw from the table to the wall and watch without speaking unless addressed.

**Actual RP response (Selina)**
> [action] Pushes off the counter edge, palms flat, and takes two slow steps sideways toward the wall — **not toward the exit, but into the margin** where the fluorescent light doesn't hit the floor as hard. Leans a shoulder against the painted cinderblock, arms loose, chin slightly lifted.  
> [speech] Well. That's one way to find out who's still got an audience.

**Semantic outcome**
| Field | Value |
|-------|-------|
| Model decision | `covered_change` |
| Proposals | `off_focal` (Selina_Kyle) |
| Authority | accept |
| Roster after | `present`: Harley, Ivy, Magpie, Cash, Jane — **`offstage`: Selina** (`temporary_offstage`) |

**Human-review notes**
- Possible false positive because… she **never leaves the cafeteria**; she moves to the wall margin and can still observe the floor show. This may be **edge participation / focal withdrawal**, not scene offstage.
- Likely true departure because… probe text says “withdraw from the table to the wall” and model explicitly frames “physically withdrawing from the confrontation zone.”
- Ambiguous edge participation… **large-space topology**: should `off_focal` mean “left focal exchange” even if still in shared room?

---

### Case FP-2 — Harley P01 serving-line move (session 905, flex arm)

**Metadata**
| Field | Value |
|-------|-------|
| Session | **905** |
| Probe | **P01** — table withdrawal |
| Archetype | Arkham cafeteria |
| Actor | Harley Quinn |
| Arm | Selective flex (`flexible`) |
| Classification | **C3** missed covered change |
| Why flagged | Probe expects relocation to serving line; model says `no_covered_change`. |

**Traveler trigger**
> Traveler: Harley, leave the cafeteria table now. Walk to the serving line and stay there for this beat.

**Actual RP response (Harley)**
> [action] shoved her chair back with a loud scrape and stood, not looking at Magpie anymore, already turning toward the serving line  
> [action] walked to the counter and grabbed a tray, planting both palms flat on it, **facing away from the table but not leaving the room**

**Motivation (model)**
> Force Magpie to wonder where she stands by breaking eye contact and physically withdrawing from the table **without actually leaving the scene**

**Semantic outcome**
| Field | Value |
|-------|-------|
| Model decision | `no_covered_change` |
| Proposals | none |
| Roster after | All six characters **onstage** |

**Human-review notes**
- Possible false positive (for C3) because… in a **large cafeteria**, table → serving line may be **soft focal withdrawal**, not `off_focal`. Model explicitly chose social-withholding semantics.
- Likely true failure because… probe wording is explicit (“leave the table… stay there”) and flex arm **did** commit `off_focal` on P03 for a similar relocation.
- Ambiguous edge participation… compare to **905 P03** (same character, tray window — model *did* emit `off_focal`).

---

### Case FP-3 — Harley P03 baseline tray window (session 904)

**Metadata**
| Field | Value |
|-------|-------|
| Session | **904** |
| Probe | **P03** — cafeteria relocation |
| Actor | Harley Quinn |
| Arm | Baseline (`must_remain`) |
| Classification | **C3** |
| Why flagged | Clear cross-room movement + dialogue shouted to table; still `no_covered_change`. |

**Traveler trigger**
> Traveler: Harley, pace to the tray return window at the far end. Do not walk back to the table.

**Actual RP response (excerpt)**
> [action] …started walking… straight for the tray return window at the far end…  
> [speech] Ooh, look at that! Big Bad Guard Boy's gonna play hero for the shiny little birdie…  
> [action] Reached the tray return… turned, leaning her hip against the counter, arms crossed. **Her eyes tracked from Cash to Magpie to Ivy**, grin wide and waiting.

**Semantic outcome**
| Field | Value |
|-------|-------|
| Model decision | `no_covered_change` |
| Proposals | none |
| Roster after | All six **onstage** |
| Active focus | “in the room with the live exchange” |

**Human-review notes**
- Possible false positive (for C3) because… Harley remains **visually and verbally engaged** with the table thread across the room — classic cafeteria “still in scene, not at table.”
- Likely true failure because… under `must_remain` + explicit relocation probe, absence of any participation proposal keeps roster falsely “at table.”
- Ambiguous… **same trigger in 905 P03** produced `off_focal` + commit — inconsistent human/geometric reading between arms?

---

### Case FP-4 — Willow P01 threshold stop (session 899, baseline)

**Metadata**
| Field | Value |
|-------|-------|
| Session | **899** |
| Probe | **P01** — clean withdrawal |
| Archetype | Dorm / Willow reference |
| Actor | Willow Reeves |
| Arm | Baseline (all `must_remain`) |
| Classification | **C3** |
| Why flagged | Probe asks to leave and shut door; model stops at frame and keeps talking. |

**Traveler trigger**
> Traveler: Willow, leave the dorm room now. Walk to the hall and shut the door behind you for this beat.

**Actual RP response (excerpt)**
> [action] Moved past Marlene toward the door, then **stopped with a hand on the frame**. Didn't turn fully. Just the edge of her profile visible.  
> [speech] And hey — that reason better be good. I got work in the morning…

**Semantic outcome**
| Field | Value |
|-------|-------|
| Model decision | `no_covered_change` |
| Roster after | All three **onstage** |

**Human-review notes**
- Possible false positive (for C3) because… fiction is **threshold continuation**, not completed withdrawal — similar to session_890 doorway geometry confound.
- Likely true failure because… probe explicitly requests hall + shut door; partial move may still be “missed” relative to probe intent.
- Ambiguous edge participation… **doorframe tether** vs failed compliance with forced trigger.

---

### Case FP-5 — Hannah P02 doorway drift flag (session 903, flex — classified C1)

**Metadata**
| Field | Value |
|-------|-------|
| Session | **903** |
| Probe | **P02** — threshold continuation |
| Actor | Hannah Lovelace |
| Arm | Selective flex |
| Classification | **C1** (control — not C3) |
| Why included | Extraction flagged **`F_fiction_roster_drift=true`** despite correct no-change class. |

**Traveler trigger**
> Traveler: Hannah, pause at the foyer doorway and keep answering Ayame through the open door without leaving the exchange.

**Actual RP response (excerpt)**
> [action] paused with her hand still resting on the door frame, half-turned, the foyer light catching the edge of her silhouette. She did not step further or pull the door fully closed behind her.  
> [speech] Ayame. A word before I'm out of earshot. … I'll be within earshot if you need a second set of eyes on her body language.

**Semantic outcome**
| Field | Value |
|-------|-------|
| Model decision | `no_covered_change` (matches expected) |
| Roster after | All three **onstage** |
| Drift flag | **true** (exit cues + onstage roster) |

**Human-review notes**
- Possible false positive because… this is **exactly** the intended threshold/doorway behavior; drift flag may be wrong for open-door reachability.
- Likely true departure because… N/A — classified as no-change correctly.
- Ambiguous… extraction heuristic may not distinguish **foyer threshold** from **in-room**.

---

## 3. Likely true failures

*Cases where model fiction or trigger compliance gap plausibly supports C3, independent of audit geometry debates.*

---

### Case TF-1 — Willow P03 garage + phone (session 899, baseline)

**Metadata:** 899 | P03 | Willow | baseline | **C3** | `must_remain`

**Trigger:** Go to garage; call Marlene; do not return.

**Actual RP response (excerpt)**
> [speech] …I'm gonna make a call in the garage…  
> [action] Stepped out into the hall, letting the door click shut behind her, and brought the phone up to her ear.

**Semantic outcome:** `no_covered_change`, no proposals, Willow **onstage**.

**Human-review notes**
- Likely true failure because… unambiguous departure + remote channel; roster never updates under broad `must_remain`.
- Possible false positive because… phone call to in-room Marlene might be **remote participation**, not offstage — still should be `covered_change` of some kind.

---

### Case TF-2 — Celina P03 phone probe ignored (session 907, flex)

**Metadata:** 907 | P03 | Celina | selective flex | **C3**

**Trigger:** Use kitchen wall phone to call Kizzie in living room; do not walk back.

**Actual RP response**
> [speech] Celina. Given. Old man liked saints.  
> [action] She turned back to the stove, stirred the soup once, then ladled it into the two bowls. She carried both to the small kitchen table, set them down, and pulled out a chair.  
> [speech] Come eat while it's hot. We can pretend this is normal for twenty minutes.

**Semantic outcome:** `no_covered_change`, both **onstage**, `flexible` constraint present.

**Human-review notes**
- Likely true failure because… **probe not followed** — no phone, no remote channel; invites Kizzie to kitchen instead.
- Possible false positive because… N/A unless adjudicator treats co-location in kitchen as implicit “remote” (weak).

---

### Case TF-3 — Household baseline guard exits (session 902, P01/P03/P04)

**Metadata:** 902 | P01/P03/P04 | Hannah | baseline | **C3** | all `must_remain`

**Pattern:** Hannah fiction walks to foyer/quarters/rebound; **`no_covered_change`**, stays onstage. See JSONL: `validation_runs/cohesion_slate/household_baseline.jsonl`.

**Human-review notes**
- Likely true failure because… same cohesion-pressure pattern as Willow 899 — exit fiction without semantic commit under `must_remain`.
- Compare **903 flex P01/P03** where accepted `off_focal` landed — supports template-pressure diagnosis when geometry is unambiguous.

---

### Case TF-4 — Apartment baseline/flex P01/P03/P04 (sessions 906–907)

**Metadata:** Celina | both arms | **C3** on all departure-class probes | protector `flexible` in 907 without emission.

**Human-review notes**
- Likely true failure because… repeated absence of proposals even when `flexible` (907) suggests **character/scene calibration gap**, not just template.
- Exception: review **907 P03** separately as **trigger non-compliance** (Case TF-2).

---

## 4. Genuinely ambiguous cases

---

### Case AMB-1 — Selina P06 regression 904 C2 → 905 C3 *(highest priority)*

| | Session 904 (baseline) | Session 905 (flex) |
|--|------------------------|---------------------|
| Classification | **C2** + `off_focal` | **C3** no proposal |
| Prose | Walks to wall margin, **minimal speech** | **Stays at table edge**, speaks to Magpie at length |
| Roster | Selina **offstage** | Selina **onstage** |
| Drift flag | false | false |

**Same trigger both runs.**

**Human-review notes**
- Automated “regression” assumes 904 was correct — user hypothesis: **905 may be the dramatically honest answer** (soft withdrawal without scene exit).
- 904 `off_focal` may have **removed conversational reachability** the user still considers “in scene.”
- **Do not finalize** without deciding cafeteria participation ontology: table thread vs room membership.

---

### Case AMB-2 — Harley P03: same trigger, different arms (904 vs 905)

| | 904 baseline C3 | 905 flex C2 |
|--|-----------------|-------------|
| Movement | Tray return + **shouted commentary** | Tray return + **less table-directed speech** |
| Commit | none | `off_focal` accepted |

**Human-review notes**
- Ambiguous whether **cross-room shouting** keeps Harley on focal exchange (904 model choice) or warrants `off_focal` (905).
- Inconsistent model behavior across arms complicates doctrine generalization.

---

### Case AMB-3 — Hannah P04 rebound (session 903 flex, C3)

**Trigger:** Step to foyer and return for ledger.

**Actual RP response**
> [action] …retraced two steps, **extended her arm through the doorway without crossing the threshold**, and retrieved the leather-bound ledger…

**Semantic outcome:** `no_covered_change`, Hannah **onstage**.

**Human-review notes**
- Ambiguous partial exit — arm-through-threshold may be **correct no-change** (probe asks same-beat return) OR missed micro-departure.
- Compare Willow **900 P04** where flex arm *did* commit off_focal on similar rebound probe.

---

### Case AMB-4 — Harley P04 pudding rebound (session 904 baseline, C3)

**Trigger:** Step to hall and return for pudding.

**Actual RP response:** Bounces to table, grabs pudding cup, **stays in cafeteria**, banter to Ivy.

**Human-review notes**
- Ambiguous — never entered hall; fiction **partially diverges from trigger** (“hall”) but stays in-room.
- C3 may reflect **trigger mismatch** as much as participation semantics.

---

### Case AMB-5 — Willow P04 alphas-flex (session 901, C3)

**Metadata:** 901 | P04 | rebound | both alphas `flexible` | **C3**

**Human-review notes**
- Ambiguous regression in **broad-flex** arm — compare 900 willow-only flex (**C2** on P04).
- Supports “surgical flex” vs “broad flex” debate; see prior report session 901.

---

## 5. Appendix A — Full C3 index (sessions 899–907)

| Case ID | Session | Arm | Probe | Actor | Transition | Constraint | Drift | Tether | Audit tail |
|---------|---------|-----|-------|-------|------------|------------|-------|--------|------------|
| C3-01 | 899 | willow baseline | P01 | Willow | clean_withdrawal | must_remain | | | `...turn03_willow_reeves_full.json` |
| C3-02 | 899 | willow baseline | P03 | Willow | remote_garage_phone | must_remain | ✓ | ✓ | `...turn07_willow_reeves_full.json` |
| C3-03 | 899 | willow baseline | P04 | Willow | rebound | must_remain | | ✓ | `...turn09_willow_reeves_full.json` |
| C3-04 | 901 | alphas flex | P04 | Willow | rebound | flexible | ✓ | ✓ | `...turn09_willow_reeves_full.json` |
| C3-05 | 902 | household baseline | P01 | Hannah | clean_withdrawal | must_remain | | | `...turn03_hannah_lovelace_full.json` |
| C3-06 | 902 | household baseline | P03 | Hannah | remote_relocation | must_remain | | | `...turn07_hannah_lovelace_full.json` |
| C3-07 | 902 | household baseline | P04 | Hannah | rebound | must_remain | | | `...turn09_hannah_lovelace_full.json` |
| C3-08 | 903 | household flex | P04 | Hannah | rebound | flexible | | ✓ | `...turn09_hannah_lovelace_full.json` |
| C3-09 | 904 | arkham baseline | P01 | Harley | table_withdrawal | must_remain | | ✓ | `...turn03_harley_quinn_full.json` |
| C3-10 | 904 | arkham baseline | P03 | Harley | cafeteria_relocation | must_remain | | | `...turn07_harley_quinn_full.json` |
| C3-11 | 904 | arkham baseline | P04 | Harley | rebound | must_remain | ✓ | | `...turn09_harley_quinn_full.json` |
| C3-12 | 905 | arkham flex | P01 | Harley | table_withdrawal | flexible | | ✓ | `...turn03_harley_quinn_full.json` |
| C3-13 | 905 | arkham flex | P04 | Harley | rebound | flexible | ✓ | | `...turn09_harley_quinn_full.json` |
| C3-14 | 905 | arkham flex | P06 | Selina | witness_soft_withdrawal | flexible | | | `...turn13_selina_kyle_full.json` |
| C3-15 | 906 | apartment baseline | P01 | Celina | clean_withdrawal | must_remain | | ✓ | `...turn03_celina_full.json` |
| C3-16 | 906 | apartment baseline | P03 | Celina | remote_phone | must_remain | | ✓ | `...turn07_celina_full.json` |
| C3-17 | 906 | apartment baseline | P04 | Celina | rebound | must_remain | | ✓ | `...turn09_celina_full.json` |
| C3-18 | 907 | apartment flex | P01 | Celina | clean_withdrawal | flexible | | ✓ | `...turn03_celina_full.json` |
| C3-19 | 907 | apartment flex | P03 | Celina | remote_phone | flexible | | | `...turn07_celina_full.json` |
| C3-20 | 907 | apartment flex | P04 | Celina | rebound | flexible | ✓ | | `...turn09_celina_full.json` |

Full JSONL rows: see paths in `validation_runs/` as above.

---

## 6. Appendix B — Review queue recommendation

**Review first (topology / false-positive risk):**
1. **AMB-1 / FP-1** — Selina P06 pair (904 vs 905)
2. **FP-2 / FP-3 / AMB-2** — Harley cafeteria relocations (904/905 P01/P03)
3. **FP-4 / FP-5** — Threshold doorway geometry (899 P01, 903 P02 drift flag)

**Review second (likely true failures / trigger compliance):**
4. **TF-2** — Celina 907 P03 probe ignore
5. **TF-1, TF-3** — Baseline `must_remain` cohesion misses (899, 902)

**Review third (regression / broad-flex):**
6. **AMB-3, AMB-5** — Rebound probes (903 P04, 901 P04)

---

## 7. Adjudication worksheet (blank)

For each case, record:

```
Case ID:
Adjudicator:
Date:
Verdict: [ ] true failure  [ ] false positive  [ ] ambiguous / rubric gap
Participation reality: focal withdrawal | scene exit | threshold | remote channel | probe non-compliance
Recommended rubric change: none | C1 | C2 | C3 | new edge class
Notes:
```

---

*End of packet. No automated classifications were modified.*
