# V2 Opening / Bootstrap Parity — M12.6

**Status:** Complete  
**Date:** 2026-08-18  
**M12.5 anchor:** `46f2000`  
**M12.6 completion HEAD:** (see §25 after commit)

**Objective:** Complete useful Holy Grail opening/bootstrap behaviors in permanent V2 architecture so production sessions can start without any deleted V1 runtime.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `46f2000` (`docs(governance): record M12.5 validation HEAD`) |
| `origin/main` | aligned at activation |
| Working tree | clean at activation |
| Workflow | assigned standard / effective **full** |
| Bootstrap profile | full V2 implementation |

### Validation baseline (pre-slice)

| Suite | Result |
|-------|--------|
| V2 Python | 116 passed, 1 xfailed |
| V2 Node | 51 passed |
| Neutral domain | 358 passed |

### Validation (post-slice)

| Suite | Result |
|-------|--------|
| V2 Python | **122 passed, 1 xfailed** |
| V2 Node | **55 passed** |
| Neutral domain | **358 passed** |

---

## 2. Reconstructed V1 opening/bootstrap behavior

| V1 behavior | Evidence | Semantic category |
|-------------|----------|-------------------|
| Minimal / premise-only start | M9 spec, `scene_template.premise` | Authoritative initial state only |
| Custom opening text | `ui_sidebar_opening`, M9 | Authored presentation |
| Template opener picker | `#101`, opener JSON assets | Authored presentation |
| Role assignment for templates | `scene_template.role_slots` | Authoritative initial state |
| LLM-generated opening (`STREAMLIT_OPENING_MODE_GENERATED`) | V1 sidebar, M12 assessment | Generated presentation (non-canon) |
| `bootstrap_composition` / interpretation snapshot | V1 headless, `#94` | Generated setup proposal + observational audit |
| `character_asset` opener mode (Streamlit) | `#108` — not Streamlit path | Authored presentation (headless/CLI only) |
| Character-card `_initial_message.json` | `scene_opener.py` | Authored presentation assets (catalog exists; no separate UI mode) |
| Narrator posts opening as chat | V1 scene start | Presentation durability via history |

---

## 3. Pre-M12.6 V2 opening state

| Mode | Domain Host | Application API | Streamlit | Gap |
|------|-------------|-----------------|-----------|-----|
| `minimal` | Partial — premise duplicated into history | Yes | Yes | History bug (premise written as opening entry) |
| `custom` | Yes | Yes | Yes | None |
| `template` | Yes (`OpenerManager`) | Catalog only | **Missing** | No opener picker / role UI |
| `generated` | **Missing** | **Missing** | **Missing** | Full bootstrap inference path |

---

## 4. Final opening-mode model

| Mode | Status | Product purpose |
|------|--------|-----------------|
| `minimal` | **Retained** (refined) | Fast deterministic start; premise in `SceneState` only |
| `custom` | **Retained** | User-authored opening prose |
| `template` | **Retained** (completed) | Authored template opener assets |
| `generated` | **Retained** (new) | LLM intro prose from authoritative setup |
| `character_asset` (V1 UI mode) | **Rejected** | Superseded by template/custom; headless-only V1 path |
| `bootstrap_composition` | **Rejected** | V1 observational/headless mechanism; not product launcher behavior |

---

## 5. Opening authority model

| Concern | Owner | Canon? |
|---------|-------|--------|
| Cast, location, template roles, premise | Domain Host / Continuity | **Yes** |
| Authored opener text (template/custom) | Domain Host resolution → `rp_history` | Presentation only |
| Generated opening prose | DSH inference → Domain Host persist | Presentation only |
| Generated facts | N/A — instruction forbids invention | **Never silent canon** |

Invariant: generated prose cannot mutate `SceneState` or continuity anchors. `persist_opening_presentation` writes history only.

---

## 6. Template/card opener architecture

```text
scene_template_id + opener_id (UI)
    → POST /v1/sessions/create { opening: { mode: "template", opener_id } }
    → Domain Host OpenerManager.resolve at create time (setup snapshot frozen)
    → rp_history kind=opening entry_id=opening-{hg_session_id}
```

Character-card `_initial_message.json` assets remain available via `OpenerManager.get_character_openers` for future catalog expansion; M12.6 does not add a separate Streamlit mode (per V1 `#108`).

---

## 7. Generated-opening architecture

```text
POST /v1/sessions/create { opening: { mode: "generated" } }
    → authoritative setup persisted, no opening history
    → ApplicationClient._generateAndPersistOpening
        → POST /v1/opening/context/prepare (PromptContributionManifest)
        → HgPhaseExecutors.runOpening (DSH ephemeral inference)
        → POST /v1/sessions/opening/persist
```

Bounded retry: 2 attempts (`opening-phase.mjs`). On failure: session remains valid; no opening history; user may proceed.

---

## 8. Context assembly / inference design

`prepare_opening_context` projects:

- `scene_state`, `continuity_canon`, `scene_grounding` (via `project_authoritative_context`, role=narrator)
- `scene_reference` (template premise)
- `character_profile` (public card fields from setup snapshot)
- `inference_instruction` (presentation-only rules)

Uses standard `PromptContributionManifest` → `HgContextBridge` path. Not a normal RP round (`hg_round_id = opening-bootstrap`).

---

## 9. Multi-character / player opening behavior

- Opening prose is **narrator-level** (single block).
- Multi-character casts: all present characters included in authoritative context; no per-character opening inferences.
- Player/user enters after opening via normal `submitUserTurn`; no player-character settings UX in this slice.

---

## 10. Session/application API changes

| Operation | Transport |
|-----------|-----------|
| `listTemplateOpeners` | `GET /v1/catalog/scene-templates/{id}/openers` (existing) |
| `createSession` with opening config | `POST /v1/sessions/create` |
| `prepareOpeningContext` | `POST /v1/opening/context/prepare` |
| `persistOpening` | `POST /v1/sessions/opening/persist` |
| Generated opening orchestration | `HolyGrailApplicationClient.createSession` / `generateOpening` |

---

## 11. Streamlit setup UX

Opening modes: **Minimal**, **Custom**, **Template**, **Generated**.

- Template selected → role assignment pickers + opener picker (via application API).
- Custom → text area.
- Generated → no extra fields.
- Create session returns transcript including opening when present.

---

## 12. Persistence / history model

- Kind: `opening`
- Stable ID: `opening-{hg_session_id}`
- Provenance metadata: `mode`, `opener_id`, `inference_id`, `manifest_id`, `label`
- `presentation_status`: `authored` | `rendered` | `failed`
- Transcript projection: Narrator assistant message with `opening: true`

---

## 13. Failure / idempotency semantics

| Failure | Behavior |
|---------|----------|
| Unknown template opener | `create_session` raises before invalid session |
| Invalid role assignments | `create_session` raises (existing) |
| Generated inference failure | Session exists; no opening entry; recoverable |
| Persist retry | `entry_id` idempotency — no duplicate openings |
| Reopen session | Opening restored from history; `prepare_opening_context` blocked |

---

## 14. Traceability

New DSH execution events (evidence only, not canon):

- `hg/opening-started`
- `hg/opening-completed`
- `hg/opening-failed`

Correlate: `hg_session_id`, `inference_id`, `manifest_id`, `presentation_text`.

---

## 15. Restart/resume proof

Covered by:

- `test_opening_bootstrap_m12_6.py::test_restart_restores_opening_without_regeneration`
- `opening-bootstrap.test.mjs` restart + user turn test

---

## 16. Real template/card proof

`celina_apartment_recovery_watch` + `kizzie`/`willow` + template opener `default` → durable Celina opener prose → user turn succeeds (Node integration test).

---

## 17. Generated-opening proof

- **Deterministic:** `opening-bootstrap.test.mjs` with `mockOpeningResponses`
- **Live DeepSeek:** deferred (credentials not required for slice completion; mock path proves architecture)

---

## 18. Minimal/custom regression proof

- Minimal: no `rp_history` opening entry; premise in `SceneState` (Python + Node tests)
- Custom: durable opening on create and reopen (existing M9 + M12.6 tests)

---

## 19. V1 parity decision matrix

| V1 behavior | V2 status | Decision |
|-------------|-----------|----------|
| Premise-only start | `minimal` | Retained |
| Custom opening text | `custom` | Retained |
| Template opener picker | `template` + Streamlit | Retained (completed) |
| Role assignment UI | Streamlit role pickers | Retained (minimal) |
| Generated LLM opening | `generated` + DSH phase | Retained |
| `bootstrap_composition` | Not implemented | Intentionally rejected (headless observational) |
| `character_asset` Streamlit mode | Not implemented | Intentionally rejected (`#108`) |
| V1 narrator opening round | Separate bootstrap phase | Redesigned (not a normal round) |
| Card-file scanning in UI | API catalog only | Rejected |

---

## 20. Product-completion impact

**Is opening/bootstrap still a blocker?** **No.**

Remaining M12 product gaps (post-M12.6):

1. Retrieval-index capability
2. Richer player/settings UX
3. Optional narrator semantic retry
4. Optional audit/debug UI

---

## 21. Clean-V2 review

| Class | Items |
|-------|-------|
| **Permanent** | `session_setup` opening modes, `prepare_opening_context`, `persist_opening_presentation`, `opening-phase.mjs`, durable `rp_history` opening, Streamlit opening controls |
| **Reused** | `OpenerManager`, `SceneTemplateManager`, `HgContextBridge`, ephemeral inference substrate |
| **Superseded/rejected** | V1 `bootstrap_composition`, Streamlit `character_asset` mode, V1 opening orchestration |
| **Deferred** | Character-card opener picker as separate mode; live DeepSeek opening smoke in CI |
| **Test-only** | `mockOpeningResponses`, synthetic opener fixtures |

---

## 22. Challenge/refinement

| Question | Answer |
|----------|--------|
| Useful behavior vs old structure? | Yes — semantics ported, V1 runtime not recreated |
| Authoritative setup Domain-owned? | Yes |
| Generated prose silent canon? | No — presentation-only persist |
| Authored openers snapshot-stable? | Yes — resolved at create |
| Minimal still cheap? | Yes — no LLM, no fake history |
| DSH substrate reused? | Yes — `runOpening` + manifest bridge |
| Opening durable? | Yes — `rp_history` |
| Reopen avoids regeneration? | Yes |
| Failures recoverable? | Yes — generated failure non-destructive |
| Distinct from normal round? | Yes — `opening-bootstrap` round id |
| UI consumer only? | Yes |
| Broader settings migration? | No |

---

## 23. Architecture verdict

**Validated with refinements** — template bootstrap completed; generated opening uses presentation-only DSH path; V1 `character_asset` / `bootstrap_composition` explicitly rejected.

---

## 24. Next recommended migration slice

**M12.7 — Retrieval-index capability** (or governance review to reprioritize player/settings UX).

Do not implement without Governance review.

---

## 25. Repository state

Recorded after commit/push in this slice.

---

## 26. Key files

| Area | Path |
|------|------|
| Session setup | `v2/domain_api/session_setup.py` |
| Opening context | `v2/domain_api/kernel.py` (`prepare_opening_context`, `persist_opening_presentation`) |
| Opening prompt | `v2/domain_api/opening_prompt.py` |
| DSH phase | `v2/rp_runtime/src/plugins/hg-phase-executors/opening-phase.mjs` |
| Application | `v2/rp_runtime/src/application/hg-application-client.mjs` |
| UI | `v2/ui/streamlit_app.py` |
| Tests | `v2/tests/test_opening_bootstrap_m12_6.py`, `v2/rp_runtime/tests/opening-bootstrap.test.mjs` |
