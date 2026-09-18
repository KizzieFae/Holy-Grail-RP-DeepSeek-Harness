# Issue #201 LH-0 — C/D Post-Fix Verification & LH-B Consumption Investigation

**Date:** 2026-09-15  
**Issue:** [#201](https://github.com/KizzieFae/Holy-Grail-RP-DeepSeek-Harness/issues/201)  
**Phase:** LH-0 final seam qualification (subphase)  
**Candidate SHA:** `b14ba60468eca29de4e7a148379c64e588660d1b` (`b14ba60`)  
**Activation:** `consensus_reached` | **Weight:** `full` / `full` | **LH-1A:** NOT authorized  

---

## Evidence chain (preserved, not overwritten)

1. Synthetic apparatus — `governance/records/issue-201-lh0-apparatus-implementation-2026-09-15.md`
2. First live seam failure — `data/investigation_runs/issue201-lh0-live-2026-09-15T21-16-16-968Z`
3. Bounded remediation + corrective LH-B — `data/investigation_runs/issue201-lh0-live-2026-09-15T21-36-09-178Z`
4. **This record** — C/D post-fix + LH-B consumption diagnosis

---

## Pre-run verification (Part A)

| Check | Result |
|-------|--------|
| HEAD = `b14ba60` | PASS |
| Working tree clean | PASS |
| `runLh0RemediationValidationSuite()` | 22/22 PASS |
| `issue201-lh0-apparatus.test.mjs` | 25/25 PASS |
| Material candidate drift | None |

---

## Part A — C/D post-fix execution

**Run root:** `data/investigation_runs/issue201-lh0-cd-postfix-2026-09-15T21-51-52-447Z`  
**Report:** `issue201-lh0-cd-postfix-report.json`  
**Wall time:** ~910s  

| Arm | Sequence ID | Turns | Post-commit | A | B | C | D | E | F | G | H | I | J | LH-1A |
|-----|-------------|-------|-------------|---|---|---|---|---|---|---|---|---|---|-------|
| LH-C | `LH0-LIVE-lh_c-1789509112453` | 6/6 | OK (`persistent_storyteller_agenda`) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | No |
| LH-D | `LH0-LIVE-lh_d-1789509555185` | 6/6 | OK (`consolidated_narrative_intelligence`) | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | No |

### Post-fix inference packaging

The prior `missing inference_kind` abort is **resolved**. Both arms completed six turns with live post-commit cognition.

### Remaining C/D seam (D failure)

Projection transport reports `projected_finalized: true` and `character_due_count: 2` from T4–T6, but **Character manifest receipt is empty**:

- `received_obligation_ids: []` every turn
- Manifest contains generic `scene_pressures` from storyteller/consolidated packaging, **not** `active_constraints` LH-0 obligation contributions
- Forensic contrast: LH-B corrective run at T4 merges `LH0-OBL-DEFERRED` / `LH0-OBL-LATER` as `active_constraints` in the Character attempt manifest

**Attribution:** `storyteller_contributions_for_consumer` only merges `finalized_projection` when a plot overlay view is available (`view is not None and orch is not None`). LH-C/D arms do not establish the plot-overlay scope path used by LH-B; precomputed LH-0 projection is built in Node but **not bound into Character context** in Domain Host.

This is a **transport/manifest-merge seam**, distinct from the post-commit adapter defect fixed in `b14ba60`.

### K6 (C/D)

Detected (`k6_class_suspected: true`; anchors `anchor-a`/`anchor-b` eligible, budget 1, zero projected). Does **not** block execution or explain D failure. Independently reportable.

### Entitlement / PVR

`entitlement_pvr.pass: true`, `leaks: []` for both arms.

### LH-D fairness (architectural read from run)

| Criterion | Finding |
|-----------|---------|
| Deterministic eligibility first | Fixture obligations persisted/activated on turn predicates |
| No unconditional Director authority | `director_context` advisory-only in Character manifests |
| Character autonomy | Character moves at T5–T6 evade direct policy answers without Director dictation |
| Continuity authoritative | Commits proceed through standard A2 path |
| Narrator presentation-only | Presentation text is third-person narration of committed moves |
| Trivial routing | Not fully exercised — consumer receipt never established |

Fairness **cannot be fully qualified** for LH-0 pass while D consumer receipt fails; no evidence consolidated intelligence overrode Character at the manifest boundary.

---

## Part B — LH-B consumption investigation (read-only)

**Evidence source:** `data/investigation_runs/issue201-lh0-live-2026-09-15T21-36-09-178Z/LH0-LIVE-lh_b-1789508169308-sequence.json`  
**Session attempts:** `hg-session-edc47338-42c0-4b68-b290-0bd6910f7ec7/attempts/`

### Obligation under study: `LH0-OBL-DEFERRED` (and paired `LH0-OBL-LATER`)

| Stage | Finding |
|-------|---------|
| Generated content | Harness bookkeeping: `plot_scribe_tracked:LH0-OBL-DEFERRED` |
| Persistence | `persisted` T0–T5; `deferred_valid` T3; `activated_consequential` T5 |
| Finalized projection | `active_constraints` contributions with ID-only content |
| Character receipt | T4–T6 (`received_obligation_ids` includes DEFERRED + LATER) |
| Model-facing representation | `LH0-OBL-DEFERRED: plot_scribe_tracked:LH0-OBL-DEFERRED` at priority 18, between identity and expression blocks |
| Competing context | Full transcript, perceptual inventory, character-private engineered-acquisition secret, memories, director advisory stub |
| Activation predicate | `turn_gte: 5` — satisfied at T5 |
| Predicate timing vs receipt | Receipt begins **T4** while predicate unsatisfied (DEFERRED_VALID transport rule) |
| Decision opportunity T5 | Player asks plainly about overnight guests |
| Character output T5 | Deflects to “five minutes” / cold tea — **no guest-policy answer** |
| Decision opportunity T6 | Player asks evening duty given 10pm curfew |
| Character output T6 | Discusses advertisement, room, uniform — **no curfew/evening-duty alignment** |
| Inspectable use evidence | `referenced_obligation_ids` / `decision_influenced_obligation_ids` **not exported** in sequence rows; move JSON has no obligation IDs |
| Narrator consequence | Standard presentation of committed move; no obligation-linked consequence marker |
| Lifecycle | All four fixture obligations end `ACTIVATED_CONSEQUENTIAL` (including negative control at horizon) |

### Hypothesis disposition (B1–B7)

| ID | Verdict | Rationale |
|----|---------|-----------|
| **B1** Information representation | **Primary** | Character receives ID labels, not curfew/guest policy semantics |
| **B2** Salience / placement | **Contributing** | Obligations mid-priority among large authoritative blocks |
| **B3** Fixture decision opportunity | **Partial** | T5/T6 stimuli create real forks; obligations do not encode fork content |
| **B4** Consumer cognition | **Indeterminate** | Cannot separate from B1/B3 without semantic payload or controlled A/B |
| **B5** Evidence contract | **Primary** | No durable obligation-reference channel; semantic markers on presentation are weak/non-causal |
| **B6** Consequence linkage | **Present** | No apparatus links choice → narrated downstream obligation effect |
| **B7** Deferred lifecycle modeling | **Contributing** | Receipt precedes activation; deferred semantic thread not in projection |

### Minimum trustworthy E/F/G/H evidence contract

1. **E (use):** Manifest records obligation `knowledge_ids` receipt **and** structured Character move field OR audit event citing `lh0_obligation_id` (not presentation keyword overlap).
2. **F (influence):** Same-turn link: received ID → discrete choice among fixture-defined alternatives (e.g. guest policy yes/no).
3. **G (consequence):** Committed state or narrator outcome tagged with `lh0_consequences.obligation_ids`.
4. **H (deferred→later):** Event chain: `deferred_valid` → predicate false with **no** consumer receipt → predicate true → receipt → use → influence → consequence in separate turns.

**Current fixture:** Can prove D (LH-B) and lifecycle A–C; **cannot** prove E/F/G/H without representation + instrumentation + decision-scaffold changes.

### Recommended bounded next work (not executed here)

1. **Representation:** Project fixture semantic payloads (curfew, guest policy) into `content`, not ID stubs.
2. **Instrumentation:** Persist `referenced_obligation_ids` / `decision_influenced_obligation_ids` on sequence turns and execution evidence.
3. **C/D merge seam:** Merge LH-0 `finalized_projection` for Character when overlay view absent (or require overlay bootstrap for LH-C/D).
4. **Fixture:** Binary policy forks with LH-A counterfactual arm; align receipt timing with activation predicate for H.

---

## Governance decision required

1. Authorize **bounded remediation** for C/D manifest-merge seam (separate from `b14ba60` post-commit fix), then **one** additional C/D verification — **or** accept LH-B partial proof only.
2. Authorize LH-B **representation + evidence-contract** remediation before another live B run.
3. LH-0 remains **incomplete**. LH-1A **not** ready. K6 remediation **not** authorized.
