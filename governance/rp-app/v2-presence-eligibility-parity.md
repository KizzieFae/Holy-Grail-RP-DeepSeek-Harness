# V2 Presence and Eligibility Parity — Implementation Report

**Status:** Completed (presence/eligibility authoritative seam slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Generic round anchor:** `3066134`  
**Implementation HEAD:** `775944d`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `3066134` |
| Workflow | assigned standard, effective **full** |
| Pre-slice validation | 16 Python + 18 Node tests green |

---

## 2. Authoritative V1 presence contract (verified)

| Concept | V1 source | Semantics |
|---------|-----------|-----------|
| Cast membership | scene fixture / participant list | Characters in the active scene cast |
| Present | `SceneState.present_characters` | On-stage, focal participants |
| Offstage | `SceneState.offstage_characters` | Temporarily off-focal; ineligible |
| Absent but relevant | `SceneState.absent_but_relevant` | Not present; ineligible |
| Eligible present mapping | `eligible_agent_keys_for_present_characters` | Maps display names → cast keys |
| Available actors | `get_available_actors(cast, used, eligible_present, offstage)` | Present + unused + not offstage |
| Presence mutation | `process_turn` via resolved mutations | Structured `off_focal` / `reentry` / excursion proposals |
| Issue #240 wire | `semantic_evaluation.proposals` | Promoted to root `semantic_proposals` at commit via `normalize_issue240_semantic_evaluation_for_continuity` |

**Cast ≠ presence.** Eligibility is never inferred from DSH session history.

**Deferred (out of scope):** continuation override, forced speaker, participation fairness.

---

## 3. Known upstream regression analysis

**Test:** `test_descriptive_exit_updates_authoritative_presence_state`

| Aspect | Finding |
|--------|---------|
| Expected | Descriptive exit prose removes Mira from `present_characters`, adds to `absent_but_relevant` |
| Actual V1 | Mira remains in `present_characters` without structured proposals |
| Authoritative path | Structured `semantic_evaluation` + `off_focal` proposal (or legacy `presence_changes`) |
| V2 impact | V2 uses the authoritative structured path; does not reproduce heuristic descriptive-exit behavior |
| Action | Not fixed in this slice; discrepancy recorded explicitly |

---

## 4. V2 eligibility architecture

**Single seam:** `POST /v1/rounds/eligible-actors` → `DomainKernel.eligible_actors()` → `_eligibility_projection()`

```text
SceneState (ContinuityManager)
  → _presence_status / _exclusion_reason per cast member
  → get_available_actors + eligible_agent_keys_for_present_characters
  → EligibleActorsResponse
  → runRound() loop (DSH consumes; never recomputes)
  → validate_director_decision (domain rejection of ineligible selection)
```

**State ownership:** Python `ContinuityManager.scene_state` only. DSH records eligibility snapshots on execution events; no local presence cache.

**Commit path:** `commit_move` applies `normalize_issue240_semantic_evaluation_for_continuity` before `process_turn` (V1 parity).

---

## 5. Dynamic presence proof

Deterministic two-character round:

1. Alice present and eligible.
2. Alice commits `off_focal` via `semantic_evaluation.proposals`.
3. Continuity moves Alice to `offstage_characters`, removes from `present_characters`.
4. Next eligibility query returns Bob only.
5. Director selecting Alice is domain-rejected.
6. Bob completes; round ends `no_eligible_actors`.

Covered by `v2/tests/test_domain_api_presence_eligibility.py` and `v2/rp_runtime/tests/presence-eligibility.test.mjs`.

---

## 6. Director validation

- Parse accepts any cast member structurally.
- Domain rule rejects ineligible `next_actor` with exclusion reason (`offstage`, `already_used_this_round`, `absent_but_relevant`, `not_in_cast`).
- Tests: `test_director_rejects_offstage_actor`, Node director-rejection integration test.

---

## 7. No-eligible-actors behavior

Unchanged from generic round slice:

- Skip Director when eligible set is empty.
- Complete with `no_eligible_actors` (semantic completion).
- Emit `hg/eligibility-exhausted` with final snapshot.
- Do not mutate continuity on exhaustion alone.

---

## 8. Traceability

| Event | Fields |
|-------|--------|
| `hg/eligibility-snapshot` | `eligibility_snapshot` (eligible, used, present, offstage, absent, per-actor entries) |
| `hg/eligibility-exhausted` | final snapshot before semantic completion |
| `hg/director-proposed/rejected/accepted` | `eligibility_snapshot` at decision time |

---

## 9. Cordis/plugin boundary

**Conclusion:** Keep presence/eligibility in the **Holy Grail domain kernel** (`DomainKernel`). Expose via existing Domain API. `HolyGrailRpRuntime` consumes projections; **no new Cordis plugin**. Domain truth stays in Python; DSH records correlated evidence.

---

## 10. Component classification

| Component | Class |
|-----------|-------|
| `_eligibility_projection`, `EligibleActorEntry`, extended `EligibleActorsResponse` | **permanent** |
| `normalize_issue240_semantic_evaluation_for_continuity` in `commit_move` | **promoted** (V1 parity at commit seam) |
| `hg/eligibility-snapshot`, `hg/eligibility-exhausted` events | **permanent** |
| Prototype cast-as-present assumption in `scene_snapshot` | **superseded** |
| HTTP transport | **transitional** (replaceable) |

---

## 11. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 23 passed |
| `npm test` in `v2/rp_runtime` | 20 passed |
| V1 `test_descriptive_exit_updates_authoritative_presence_state` | **still fails** (pre-existing; documented) |
| V1 offstage / `get_available_actors` rules | pass |

---

## 12. Architecture verdict

**Validated with refinements** — eligibility is authoritative and presence-aware; commit normalization bridge required for Issue #240 wire format; descriptive-exit heuristic remains an unresolved V1 discrepancy.

---

## 13. Remaining deferred semantics

- Continuation override / forced speaker
- Participation fairness / repeat-speaker policy
- Descriptive-exit heuristic → `absent_but_relevant` (upstream ambiguity)
- Full V1 presence constraint surface (`must_remain`, excursions) in V2 tests (behavior inherited via `process_turn`)
