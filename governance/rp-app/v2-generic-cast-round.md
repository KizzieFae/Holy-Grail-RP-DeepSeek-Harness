# V2 Generic Cast Round — Implementation Report

**Status:** Completed (semantic round-completion slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Two-character slice anchor:** `8ee633b`  
**Implementation HEAD:** `d6295e1`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `8ee633b` |
| Pre-slice validation | 15 Python + 14 Node tests green |

---

## 2. Authoritative V1 round contract (verified)

| Rule | V1 source | V2 representation |
|------|-----------|-------------------|
| Director before each turn | `turn_runner.py` while loop | `runRound` loop |
| Exclude used actors | `get_available_actors` | `eligible_actors` domain API |
| `end_round` stops round | `turn_runner.py:258` | `director_end_round` completion |
| No actors → stop | `turn_runner.py:218-219` | `no_eligible_actors` (no Director call) |
| Narrator per committed turn | `execute_character_turn_render_phase` | `_runNarratorPresentation` |
| Defensive max attempts | `max_attempts` in V1 | `defensiveTurnCeiling` |
| Director failure aborts | V1 breaks on invalid selection | `director_failure` |
| Character failure preserves prior commits | V1 `continue` on failure | `character_failure` |
| Narrator failure preserves canon | established V2 rule | unchanged |

**Not yet in V2:** continuation override, forced speaker, full presence routing, participation fairness.

---

## 3. Generic runtime architecture

`runRound(options)` is the permanent API:

```text
while true:
  if character_turn_count >= defensiveTurnCeiling → defensive_turn_ceiling
  eligible = domain.getEligibleActors()
  if none → no_eligible_actors
  director phase → end_round? → director_end_round
  character phase → failure? → character_failure
  narrator phase
  repeat
```

Removed: `runDirectorCharacterRound`, `runTwoCharacterRound`, `characterTurnLimit`.

---

## 4. Completion semantics

| Reason | Class | Status |
|--------|-------|--------|
| `director_end_round` | semantic | completed |
| `no_eligible_actors` | semantic | completed |
| `defensive_turn_ceiling` | defensive | completed |
| `director_failure` | failure | aborted |
| `character_failure` | failure | aborted |

---

## 5. Eligibility model

`POST /v1/rounds/eligible-actors` uses V1 `get_available_actors`:

- cast membership
- `actors_used_this_round` exclusion
- present characters (prototype: full cast)
- offstage exclusion (when set on scene state)

Returns `character_roles` for runtime role assignment.

---

## 6. Arbitrary-cast proof

| Cast size | Completion | Tests |
|-----------|------------|-------|
| 1 | `no_eligible_actors` after single turn | director-character, generic |
| 2 | `no_eligible_actors` after both act | two-character-round |
| 3 | `no_eligible_actors` after all act | generic-round |

---

## 7–15. (See commit report sections in final deliverable)

---

## 16. Repository state

| Field | Value |
|-------|-------|
| Commit | `d6295e1` — feat(v2): complete generic cast round semantic completion |
| Branch | `main` |
| `origin/main` | aligned after push |

---

## 17. Next recommended slice

**Presence/eligibility seam** — wire offstage/presence filtering from continuity into `eligible_actors` with V1 parity tests. Requires Governance review.
