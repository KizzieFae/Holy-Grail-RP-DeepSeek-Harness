# V2 Character Cards — M12.1 Implementation Report

**Status:** Completed (M12.1 — framework-neutral character card I/O split)  
**Date:** 2026-08-18  
**M12 retirement-plan anchor:** `6c2209c`  
**Implementation HEAD:** `1c82d9b`

---

## 1. Scope

Split entangled `character_loader.py` into:

| Layer | Location | Role |
|-------|----------|------|
| Framework-neutral card I/O | `v2/domain/character_cards.py` | Permanent loader, schema, identity helpers |
| Legacy AutoGen factory | `legacy/v1_autogen_agents.py` | V1 `AssistantAgent` construction only |
| V1 compatibility shim | `autogen_rp/python/rp_app/character_loader.py` | Subclass delegating to both |

V2 production imports **only** `domain.character_cards`.

---

## 2. Previous character-loader architecture

| Responsibility | Was | Now |
|----------------|-----|-----|
| JSON load/list | `CharacterLoader` | `CharacterCardLoader` (neutral) |
| `CHARACTER_MOVE_SCHEMA` | `character_loader.py` | `domain.character_cards` |
| `make_agent_identifier` | `character_loader.py` | `domain.character_cards` |
| `normalize_relationships` | `_normalize_relationships` private | `normalize_relationships` public |
| `create_agent` / AutoGen | `CharacterLoader.create_agent` | `legacy/v1_autogen_agents.py` |
| V1 imports | `character_loader` | Shim re-exports + delegates |

---

## 3. Neutral character-card module

**Path:** `v2/domain/character_cards.py`

**API:**

- `CharacterCardLoader` — `load_character_card`, `list_available_characters`
- `CHARACTER_MOVE_SCHEMA`
- `make_agent_identifier`, `normalize_relationships`, `validate_character_card`
- `default_characters_dir()`

**Dependencies:** stdlib only (json, re, pathlib).

---

## 4. Character identity behavior

Preserved:

- `character_file_id` = JSON file stem
- canonical actor identity = card `name` field
- `names_by_file` / `character_file_ids` mapping unchanged in `session_setup`

---

## 5. CharacterState initialization

**Home:** `v2/domain_api/session_setup.py` → `create_character_state_from_card()`

Uses `normalize_relationships` from neutral module. Does not import legacy loader or AutoGen.

---

## 6. Legacy AutoGen factory

**Path:** `legacy/v1_autogen_agents.py`

- `create_character_agent(card, model_client)` → `(AssistantAgent, CharacterState)`
- `build_character_system_message(card)`
- Imports AutoGen + `model_client` only here

**Dependency direction:** legacy → neutral (never reverse).

V1 `CharacterLoader` shim delegates `create_agent` to legacy factory.

---

## 7. V2 import migration

| File | Before | After |
|------|--------|-------|
| `session_setup.py` | `character_loader.CharacterLoader` | `domain.character_cards.CharacterCardLoader` |
| `setup_catalog.py` | `character_loader.CharacterLoader` | `domain.character_cards.CharacterCardLoader` |

Static check: no `character_loader` references under `v2/domain_api/`.

---

## 8. AutoGen-free proof

- `test_import_without_autogen_in_subprocess` — subprocess imports `domain.character_cards` and loads `kizzie` without touching `rp_app` or AutoGen
- `test_v2_production_does_not_import_legacy_character_loader` — scans `v2/domain_api/*.py`

Scoped claim: **character-card I/O chain is AutoGen-free**. Other `rp_app` helpers (continuity, validation) remain for M12.2.

---

## 9. Catalog/setup/snapshot proof

Tests:

- `test_v2_session_setup_uses_neutral_loader`
- `test_catalog_uses_neutral_loader`
- Existing M9/M11 session tests remain green (102 V2 Python tests)

---

## 10. V1 compatibility proof

- `autogen_rp/python/tests/test_character_loader.py` — green (shim + legacy factory)
- `test_issue_230` character loader system prompt test — green

---

## 11. Test migration

| Test | Location |
|------|----------|
| Neutral I/O, identity, subprocess | `v2/tests/test_character_cards_m12_1.py` (9 tests) |
| AutoGen agent construction | `autogen_rp/python/tests/test_character_loader.py` (legacy) |

---

## 12. Clean-V2 cleanup

- Removed ~500 lines of duplicated I/O from `character_loader.py` (now 37-line shim)
- Single authoritative card parser in `v2/domain/character_cards.py`
- No `create_agent` on neutral loader

---

## 13. Package-boundary assessment

`v2/domain/` is suitable as M12.2 seed:

- Importable from Domain Host via `sys.path` insert of `v2/`
- No `rp_app` dependency in neutral card module
- `rp_app` shim depends on `v2/domain` + `legacy/` (correct direction)
- Supports eventual `autogen_rp` tree deletion after broader extraction

---

## 14. Retirement-map impact

| Item | Status |
|------|--------|
| Character card I/O | **extract/rehome complete** |
| AutoGen character-agent factory | **legacy-only** (`legacy/v1_autogen_agents.py`) |
| V2 card dependency on AutoGen | **removed** |

**Next extraction candidates:** `continuity_manager`, `memory_layer`, `response_validation*`, `scene_grounding` (M12.2).

---

## 15. Behavioral validation

```text
python -m pytest v2/tests/ -q                    → 102 passed (+9 M12.1)
cd v2/rp_runtime && npm test                      → 51 passed
python -m pytest autogen_rp/python/tests/test_character_loader.py -q → 2 passed
python -m pytest autogen_rp/python/tests/test_issue_230_phase_a_semantic_proposals.py::test_character_loader_system_prompt_teaches_semantic_evaluation_not_illegal_roots -q → 1 passed
```

---

## 16. Challenge/refinement

| Question | Verdict |
|----------|---------|
| Single card parser? | **Yes** |
| V2 without AutoGen for cards? | **Yes** |
| Identity unchanged? | **Yes** |
| Catalog privacy intact? | **Yes** |
| AutoGen clearly legacy? | **Yes** |
| V1 callers work? | **Yes** via shim |
| Good M12.2 foundation? | **Yes** |

---

## 17. Architecture verdict

**Validated as designed**

---

## 18. Next recommended slice

**M12.2 — Extract remaining reusable domain helpers from `rp_app` into `v2/domain/`** (continuity, memory, validation, scene_grounding). Do not implement without Governance review.
