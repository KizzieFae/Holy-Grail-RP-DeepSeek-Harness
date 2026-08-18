# V2 Two-Character Cast Loop — Implementation Report

**Status:** Completed (multi-character orchestration proof)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Three-role round anchor:** `5a77eb5`  
**Implementation HEAD:** (see §16 after commit)

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `5a77eb552429cb61931d3557376d848abb536170` |
| `origin/main` | aligned at slice start |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Pre-slice validation | 12 Python + 11 Node tests green |

---

## 2. V1 multi-character behavioral contract (discovered)

From `turn_runner.py` / `app_turn_director.py` / `response_validation_selection.py`:

| Rule | V1 behavior |
|------|-------------|
| Director invocation | **Once per character turn**, not once per round |
| Actor selection | `get_available_actors` excludes `actors_used_this_round` |
| Character may repeat | No — used actors excluded until round ends |
| Round stop | `end_round=true`, turn limit reached, or no available actors |
| Narrator timing | **After each successful character commit** (per-turn render) |
| Retries | Per-character attempt loop; failures do not add to `actors_used_this_round` |
| State authority | Python continuity commit between turns; later context from updated domain state |

This slice implements the smallest faithful two-character instance: Director → Alice → commit → Narrator → Director → Bob → commit → Narrator → round complete.

---

## 3. Runtime architecture changes

### Generalized orchestration (`HolyGrailRpRuntime`)

| Method | Role |
|--------|------|
| `runRound({ characterTurnLimit })` | N-character-capable round loop |
| `_runDirectorPhase` | Ephemeral director inference + validation |
| `_runCharacterTurn` | Ephemeral character inference + validate + commit |
| `_runNarratorPresentation` | Post-commit presentation (unchanged semantics) |
| `runDirectorCharacterRound` | Delegates to `runRound({ characterTurnLimit: 1 })` |
| `runTwoCharacterRound` | Delegates to `runRound({ characterTurnLimit: 2 })` |

### Domain API extensions

| Change | Purpose |
|--------|---------|
| `RoundFixture.character_turns` | Authoritative per-turn commit records |
| `RoundFixture.actors_used_this_round` | Director eligibility tracking |
| `prepare_director_context(actors_used_this_round)` | Sequencing context |
| `prepare_context` → `continuity_summary` | Post-commit projection for later characters |
| `validate_director_decision` | Rejects used actors; accepts `end_round` |
| `prepare_narrator_context` | Looks up specific commit by `domain_commit_id` |

### New event

- `hg/round-completed` — execution completion only (not domain truth)

### Correlation field

- `character_turn_index` — 0-based position within round trace

---

## 4. Two-character sequence

```text
hg/round-started
  → Director (available: Alice, Bob) → Alice selected
  → Character A: propose → validate → commit → hg/move-committed
  → Narrator A: render
  → Director (available: Bob; used: Alice) → Bob selected
  → Character B: propose → validate → commit (turn_index=1)
  → Narrator B: render
  → hg/round-completed
```

---

## 5. State-projection proof

| Requirement | Evidence |
|-------------|----------|
| Bob sees Alice committed action | `continuity_summary` includes blueprint placement |
| Post-commit turn counter | Bob `prepare_context` uses `turn_index=1` after Alice commit |
| Not from DSH history | Projection built in Python `prepare_context` from `character_turns` |

---

## 6. Context-isolation proof

| Requirement | Evidence |
|-------------|----------|
| Alice private → not in Bob manifest | Node + Python tests |
| Rejected Alice attempt invisible | Node rejected-attempt projection test |
| Director scratch excluded from characters | Existing isolation tests retained |
| Per-character private scoped | Bob sees only `private-Bob` in `character_private` |

---

## 7. State-authority proof

| Requirement | Evidence |
|-------------|----------|
| Independent commits | Two `hg/move-committed` events; `turn_counter=2` |
| Director rejects used actor | `test_director_rejects_already_used_actor` |
| Failed Bob cannot corrupt Alice | Commit anchor per turn; prior turn unchanged |
| Narrator failure preserves canon | Existing narrator failure tests retained |

---

## 8. Session/event topology

Unchanged topology:

- **One** scene correlation session
- **Ephemeral** sessions per Director / Character / Narrator call

Multi-character trace distinguished by: `character_turn_index`, `character_id`, `domain_commit_id`, `continuity_turn_index`, `actors_used_this_round` on director events.

---

## 9. Round-completion semantics

`hg/round-completed` recorded when:

- `character_turn_count >= characterTurnLimit`, or
- Director returns `end_round=true`, or
- Director/character phase fails

Fields: `completion_reason`, `character_turn_count`, `actors_used_this_round`, `round_completed`.

Does **not** mutate continuity.

---

## 10. Plugin/service boundary assessment

**Keep one `HolyGrailRpRuntime` Cordis service for now.**

Rationale: Director/Character/Narrator phases share ephemeral inference substrate, scene correlation, and boundary client. Extraction into separate services would duplicate correlation wiring without independent deployment boundaries yet. Revisit when plugin/component architecture matures.

---

## 11. Boundary efficiency (two-character round)

| Metric | Approximate value |
|--------|------------------|
| Total boundary calls | ~14–16 |
| Per character turn | ~7 (director prepare/validate + character prepare/validate/commit/state + narrator prepare) |
| DSH ephemeral sessions | 6 (2 director + 2 character + 2 narrator) |
| Manifest growth | `continuity_summary` adds prior committed moves per later character |
| HTTP adequacy | Comfortable for prototype; no transport change needed |

---

## 12. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | **15 passed** |
| `npm test` (v2/rp_runtime) | **14 passed** |

---

## 13. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `runRound`, phase helpers, round fixture tracking, `continuity_summary`, `hg/round-completed` |
| **Promoted** | Generalized orchestration (replaces single-character-only flow) |
| **Transitional** | HTTP transport, fixture store, mock LLM |
| **Removed** | Monolithic single-path `runDirectorCharacterNarrator` inline flow |
| **Test-only** | `two-character-round.test.mjs`, extended domain authority tests |

No `character1`/`character2` permanent architecture — only `character_turn_index` and generic loops.

---

## 14. Challenge/refinement

- Multi-character sequencing fits naturally with repeated Director phases per V1 contract
- State projection after each commit is clean via `character_turns` + `continuity_summary`
- Role isolation survived; no DSH session bleed
- Scene trace remains readable with `character_turn_index`
- `HolyGrailRpRuntime` grew but via extracted phase methods, not copy-paste
- Third/fourth character fits `runRound({ characterTurnLimit: N })` without redesign
- HTTP chatter scales linearly; acceptable for prototype
- Deferred: full V1 participation fairness, continuation override, presence routing

---

## 15. Architecture verdict

**Validated with refinements** — two-character cast loop proven with faithful V1 sequencing semantics. Refinements deferred: full participation fairness, presence eligibility, continuation override, arbitrary-N cast without explicit limit.

---

## 16. Repository state

(See commit after push.)

---

## 17. Next recommended slice

**Arbitrary cast loop with Director `end_round` completion** — remove fixed `characterTurnLimit`, loop until Director sets `end_round` or no available actors (full V1 round semantics). Requires Governance review.
