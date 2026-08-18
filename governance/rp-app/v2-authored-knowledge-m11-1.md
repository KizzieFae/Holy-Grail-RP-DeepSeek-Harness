# V2 Authored Knowledge — M11.1 Implementation Report

**Status:** Completed (M11.1 — KnowledgeService + authored snapshot retrieval)  
**Date:** 2026-08-18  
**M11 architecture anchor:** `5d1aa26`  
**Implementation HEAD:** (see §20 after commit)

---

## 1. Scope

Implement permanent `KnowledgeService` for **authored session-snapshotted** knowledge only:

- character card `lore_facts` → `authored_character_knowledge` lane;
- scene template reference fields → `scene_reference` lane;
- deterministic visibility, authority, caps, provenance;
- ContextAssembly integration via `prepare_context`;
- remove V2 `lore_facts[0]` → `character_private_secrets` hack.

**Not in scope:** learned world facts, user profile writes, databases, vectors, cross-session knowledge repository.

---

## 2. Previous authored-knowledge path

| Path | Behavior | M11.1 |
|------|----------|-------|
| `lore_facts[0]` → `character_private_secrets` | First lore line injected as `character_private` | **Removed** |
| `character_profile` | Identity instruction only | Unchanged |
| `scene_state` | Authoritative location/presence | Unchanged |
| `setup_snapshot` | Stored at M9 create | **Source for KnowledgeService** |
| V1 `RP_RETRIEVED_CONTEXT_INDEX` | Compiled index retrieval | Not wired in V2 (deferred) |

---

## 3. KnowledgeService architecture

| Module | Role |
|--------|------|
| `v2/domain_api/knowledge_service.py` | Permanent seam; `project_context()` for ContextAssembly |
| `v2/domain_api/authored_knowledge.py` | Snapshot compile, visibility filter, caps, record contract |
| `v2/domain_api/kernel.py` | Calls `KnowledgeService` in `prepare_context` |

Reuses V1 `canonical_compile_adapters.resolve_adapter_row` for `lore_facts` and template field metadata.

Stateless service — no persistence layer in M11.1.

---

## 4. Authored character knowledge

- Source: `setup_snapshot.character_cards[file_id].lore_facts`
- Compile: one record per lore line (`lore_reference`, `reference_only` → V2 `suggestive`)
- Visibility: `character_scoped` — only matching `character_file_id`
- Cap: 4 items (first in card order)
- Lore excerpt cap: 600 chars per line

---

## 5. Scene/template reference handling

- Source: `setup_snapshot.scene_template` when `scene_template_id` set
- Fields: `premise`, `tone`, `opening_text`
- Visibility: `template_participants`
- Lane: `scene_reference`, authority `suggestive`
- Cap: 3 items
- Does **not** duplicate authoritative `scene_state` (location/presence)

---

## 6. Authority model

| Canonical class | V2 `authority_class` |
|-----------------|----------------------|
| `reference_only` | `suggestive` |
| `setup_truth` | `suggestive` |
| `behavioral_guidance` | `suggestive` |

Scene state remains `authoritative`. Authored knowledge contributions include `authority_note: suggestive_reference_not_current_canon`.

---

## 7. Visibility/privacy model

Enforced in `select_authored_records()` before manifest creation:

- `character_scoped` → subject `character_file_id` only
- `template_participants` → session template match only

`system_prompt` and full card bodies are not injected. Catalog APIs unchanged (no knowledge body exposure).

---

## 8. Deterministic retrieval

- Compile from snapshot (no live file reads on `prepare_context`)
- Filter by visibility + character file ID
- Order: `source_index` (lore_facts order / template field order)
- Caps: 4 character + 3 scene reference
- Dedupe: `knowledge_id`

---

## 9. Knowledge record contract

`AuthoredKnowledgeRecord`: `knowledge_id`, `knowledge_kind`, `content`, `authority_class`, `visibility`, `subject_character_file_id?`, `source_kind`, `source_asset_id`, `provenance` (includes `setup_snapshot_hash`, `source_index`, `knowledge_lane`).

---

## 10. ContextAssembly integration

New `source_kind` values on `PromptContribution`:

| source_kind | priority | authority_class |
|-------------|----------|-----------------|
| `authored_character_knowledge` | 21+ | `suggestive` |
| `scene_reference` | 21+ | `suggestive` |
| `character_memory` | 26+ | `derived` (unchanged) |
| `character_private` | 25 | only when non-empty secret |

`character_private` omitted when no legitimate private secret exists.

---

## 11. Lore-shortcut retirement

Removed from `session_setup.py`:

```text
lore_facts[0] → character_private_secrets
```

`character_private_secrets` now only populated from `CharacterState.private_memories` when present.

---

## 12–14. Proofs (tests)

| Test | Invariant |
|------|-----------|
| `test_snapshot_stability_after_card_edit` | Reopened session retains snapshot lore after card file mutation |
| `test_authored_lore_reaches_intended_character_only` | Kizzie/Willow lore isolation |
| `test_authority_precedence_scene_state_over_authored_reference` | `scene_state` authoritative vs knowledge suggestive |
| `test_memory_and_knowledge_lanes_remain_separate` | Knowledge retrieve does not mutate episodic memory |
| `test_lore_not_in_character_private_lane` | No lore in `character_private` |

Suite: `v2/tests/test_authored_knowledge_m11_1.py` (7 tests).

---

## 15. Validation

```text
python -m pytest v2/tests/ -q  → 74 passed
cd v2/rp_runtime && npm test  → 51 passed
```

---

## 16. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `KnowledgeService`, `authored_knowledge.py`, ContextAssembly lanes |
| **Reused** | `canonical_compile_adapters` |
| **Superseded for V2** | lore-as-private-secret hack |
| **Deferred** | learned world facts, user profile, DB, vectors, compiled index env path |
| **Test-only** | synthetic lore cap fixtures |

---

## 17. V1 retirement impact

| V1 path | V2 status |
|---------|-----------|
| Direct lore → private prompt injection | Superseded |
| `RP_RETRIEVED_CONTEXT_INDEX` in V2 | Deferred (can plug into `AuthoredKnowledgeProvider` later) |
| V1 prompt-builder lore blocks | Unchanged in V1; V2 uses KnowledgeService |

---

## 18. Challenge/refinement

| Question | Verdict |
|----------|---------|
| Meaningful permanent boundary? | Yes |
| Lore shortcut removed? | Yes |
| Snapshot-only authored source? | Yes |
| Cross-character isolation? | Yes |
| Continuity higher authority? | Yes (`authoritative` vs `suggestive`) |
| Memory/knowledge distinct? | Yes |
| Deterministic and bounded? | Yes |
| Unnecessary repository abstraction? | No — compile-from-snapshot only |
| M11.2 straightforward? | Yes — add learned/profile repositories behind same seam |

---

## 19. Architecture verdict

**Validated as designed** — authored KnowledgeService boundary established; lore migration complete; ready for M11.2 learned knowledge slice.

---

## 20. Next recommended slice

**M11.2 — Scope-bound learned world facts + user profile repositories** (Governance review required).

Do not implement without Governance review.
