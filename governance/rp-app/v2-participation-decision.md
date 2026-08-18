# V2 ParticipationDecision — Implementation Report

**Status:** Completed (participation policy seam slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Presence/eligibility anchor:** `7738f00`  
**Investigation anchor:** `22b9bbc`  
**Implementation HEAD:** `bc01b47` (implementation `e30f666`, governance `bc01b47`)

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `22b9bbc` |
| Pre-slice validation | 37 Python + 23 Node tests green |

---

## 2. ParticipationDecision contract

`POST /v1/rounds/participation-decision`

| Field | Semantics |
|-------|-----------|
| `eligibility_snapshot_id` | `{hg_round_id}:{eligibility_epoch}` — staleness guard |
| `selection_mode` | `direct` \| `director` — how selection proceeds |
| `selected_actor` | Actor when `direct` |
| `director_required` | Whether Director inference is needed |
| `director_constraint_actor` | Reserved; constraint enforced via validation request |
| `participation_sources` | `forced_designation`, `continuation_preference`, or empty |
| `forced_designation_ignored` | Ineligible forced input was not applied |
| `continuation_c2_skip` | Continuation deferred to Director without constraint |

**Input:** `forced_designation` (request-scoped, optional) + current eligibility snapshot id.

---

## 3. Participation policy ordering

```text
eligibility projection (hard floor)
        ↓
forced designation eligible? → direct
        ↓
continuation inference eligible?
   ├── C2 skip → director (no constraint)
   ├── hard route → direct
   └── ineligible → director (normal)
        ↓
else → director (normal)
```

Implemented in `v2/domain_api/participation_policy.py`.

---

## 4. Forced designation

- Request-scoped via `runRound({ forcedDesignation })` — no persistent DSH/domain flags
- Consumed locally in `runRound` only after successful direct application
- Ineligible designation ignored (non-fatal); normal Director path follows
- Does not bypass presence/used-this-round eligibility

---

## 5. Continuation semantics

Re-expressed from V1 rules in `resolve_continuation_actor`:

- Last committed move + spotlight + turn metadata
- Present-unheard peer suppression; offstage unheard does not suppress
- C2: when spotlight tail matches continuation actor → Director without constraint
- Direct continuation when actor eligible and spotlight does not trigger C2

Round state: `spotlight_history`, `character_turns` on `RoundFixture`; epoch bumped on commit.

---

## 6. Generic round integration

Each loop iteration:

1. `getEligibleActors()`
2. `getParticipationDecision()` with snapshot id + optional forced designation
3. `hg/participation-decision` event
4. `direct` → synthetic director decision, skip Director inference
5. `director` → `_runDirectorPhase()` with constraint context on validation

---

## 7. Director validation extensions

- Stale `eligibility_snapshot_id` → `continuity_anchor` rejection
- `director_constraint_actor` mismatch → `domain_rule` rejection
- `continuation_c2_skip` exempts constraint enforcement (V1 C2 semantics)

---

## 8. Trace events

| Event | Purpose |
|-------|---------|
| `hg/participation-decision` | Authoritative policy result correlated to eligibility snapshot |
| `hg/eligibility-snapshot` | Eligibility floor before policy |
| `hg/director-*` | Only when `selection_mode === director` |

---

## 9. Component classification

| Component | Class |
|-----------|-------|
| `ParticipationDecision`, `participation_policy.py` | **permanent** |
| `eligibility_snapshot_id` / `eligibility_epoch` | **permanent** |
| `POST /v1/rounds/participation-decision` | **permanent** |
| `forcedDesignation` runRound option | **permanent** (request-scoped ingress) |
| HTTP transport | **transitional** |

**Not migrated:** `pending_forced_speaker`, `forced_speaker_consumed`, AutoGen selector callbacks.

---

## 10. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 37 passed |
| `npm test` (`v2/rp_runtime`) | 23 passed |
| V1 continuation/forced tests (selected) | 9 passed |

---

## 11. Architecture verdict

**Validated with refinements** — unified participation policy seam established; continuation C2 and forced designation behave per verified V1 semantics without V1 session flags.

---

## 12. Deferred

- Participation fairness
- Per-turn forced designation ingress beyond single request-scoped value
- Production user-message `detect_forced_speaker` integration at transport boundary
