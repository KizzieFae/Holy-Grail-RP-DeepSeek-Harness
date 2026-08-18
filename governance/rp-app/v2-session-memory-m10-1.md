# V2 Session-Local Memory — M10.1 Implementation Report

**Status:** Completed (M10.1 — session-local MemoryWritePolicy + context retrieval)  
**Date:** 2026-08-18  
**M10 investigation anchor:** `1a41571`  
**Implementation HEAD:** (see §19 after commit)

---

## 1. Scope

Session-local memory only:

- write on authoritative `commit_move` and `record_user_turn`;
- persist in `CharacterState` via `SessionRepository`;
- retrieve in `prepare_context` as `character_memory` contributions;
- **no** cross-session scope, `memory_scope_id`, or vector retrieval.

---

## 2. MemoryWritePolicy architecture

| Module | Role |
|--------|------|
| `v2/domain_api/memory_write_policy.py` | Domain write policy; ports V1 `memory_layer/writes` semantics |
| `v2/domain_api/memory_retrieval.py` | Deterministic episodic tail projection (5+5) |
| `v2/domain_api/kernel.py` | Hooks on `commit_move`, `record_user_turn`, `prepare_context` |

Uses existing `CharacterState` as authoritative session-local container — no second memory store.

---

## 3. Commit ordering

```text
validate_move (no memory)
    ↓
commit_move:
    process_turn (continuity)
    ↓
    MemoryWritePolicy.apply_character_turn_memory
    ↓
    SessionRepository.persist
```

On `PersistenceError`: restore `ContinuityManager` snapshot **and** `CharacterState` snapshot.

---

## 4. Character-turn memory

After successful commit:

1. `update_character_move` → `recent_observations` self-trace
2. `commit_character_turn_memory` → actor interpretation + perception-filtered observer episodic lines

Uses v2 beat flattening via `root_or_flat_action_text` / `root_or_flat_dialogue_text`.

Director interpretation ladder (#208) preserved.

---

## 5. User-turn memory (refined from V1)

**V1:** `remember_user_interaction` on **all** cast members regardless of presence/perception.

**M10.1:** Only **present** characters (`resolve_present_characters`) who **perceive** the line via `player_text_for_character_viewer` receive relationship memory.

Redacted/inaccessible lines create **no** memory for that character.

---

## 6. Context retrieval

`prepare_context` adds when episodic tails exist:

```text
source_kind: character_memory
authority_class: derived
content: interpretation summary tail (5) + recent observations tail (5)
```

`private_memories` list remains **persisted but not prompt-injected**.

---

## 7. Provenance contract

Memory contributions include provenance:

- `character_id`
- `memory_lane: session_local_episodic`
- `interpretation_line_count`, `self_trace_line_count`
- `private_memories_injected: false`

---

## 8. Validation

| Suite | Result |
|-------|--------|
| V2 Python | 59 passed (8 new M10.1 tests) |
| V2 Node | 51 passed |
| V1 `test_memory_layer_writes.py` | Unchanged (reused policy) |

---

## 9. V1 retirement impact

| V1 | M10.1 V2 replacement | Removal condition |
|----|----------------------|-------------------|
| `app_memory_recording` Streamlit hooks | Kernel `commit_move` / `record_user_turn` | V2 production path default |
| `prompt_builders` episodic injection | `prepare_context` `character_memory` | V2 manifest-only prompts |
| All-cast user memory | Perception-filtered user memory | Documented refinement |

---

## 10. Architecture verdict

**Validated as designed** — session-local lifecycle complete; M10.2 (`MemoryService` + `memory_scope_id`) is unblocked.

---

## 11. Repository state

| Commit | (pending) |

---

## 12. Next slice

**M10.2 — MemoryService interface + `memory_scope_id` + cross-scope aggregation** (Governance review required).
