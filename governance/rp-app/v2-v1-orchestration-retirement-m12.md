# V2 V1 Orchestration Retirement — M12 Investigation Report

**Status:** Completed (M12 — investigation/design only; no runtime mutation)  
**Date:** 2026-08-18  
**M11.3 authoritative-context anchor:** `0fba61f`  
**M8 V1 surface deprecation anchor:** `8f360a1`  
**Investigation HEAD:** (see §25 after commit)

**Governing objective:**

> One clean V2 product architecture — retire obsolete mechanisms, not valuable domain semantics.

**Authorization:** investigation and governance record only. No V1 deletion, package moves, or AutoGen removal in this slice.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-investigation HEAD | `0fba61fb39ed0002714b000f04032c4185bf7fa1` |
| `origin/main` | aligned |
| Workflow | assigned standard / effective **full** |
| Bootstrap profile | full V2 architecture/retirement investigation |
| Working tree | clean at investigation start |
| V1 entrypoint | `autogen_rp/python/rp_app/app.py` — **DEPRECATED (M8)** |
| Default launch | `Launch-Holy-Grail-V2.bat` → `v2/rp_runtime` |

### Pre-investigation validation

| Suite | Result |
|-------|--------|
| V2 Python (`v2/tests/`) | **93 passed** |
| V2 Node (`v2/rp_runtime/tests/`) | **51 passed** |
| V1 Python (`autogen_rp/python/tests/`) | **~154 tests** (large suite; not re-run to completion in M12 — historical CI asset) |

M11.1/M11.2/M11.3 regression suites included in V2 Python count.

---

## 2. V1 runtime dependency map

```text
app.py (DEPRECATED Streamlit entry)
  ├── app_bootstrap.run_app_startup
  ├── ui_rendering → ui_chat.render_chat
  │     └── asyncio.run(process_user_message)
  ├── app_message_processing.process_user_message
  │     ├── scene_lifecycle.recreate_team_from_state
  │     │     └── character_loader.create_agent (AutoGen AssistantAgent)
  │     ├── model_client (OpenAIChatCompletionClient)
  │     └── app_memory_recording / memory helpers
  └── turn_runner.run_character_turns
        ├── orchestration_helpers (eligibility, continuation state)
        ├── app_turn_director.choose_next_actor
        │     ├── director_prompt_payload.build_director_prompt_payload
        │     ├── prompt_builders.build_director_selection_prompt
        │     └── director agent on_messages (AutoGen TextMessage)
        ├── turn_runner_turn.execute_character_turn
        │     ├── turn_runner_character_attempt (LLM, parse, validate, semantic)
        │     │     ├── app_turn_prompting / prompt_topology_issue240
        │     │     ├── prompt_retrieval_assembly (index + episodic select)
        │     │     └── response_validation / semantic_validation
        │     └── turn_runner_character_render (narrator LLM + semantic review)
        │           ├── app_turn_rendering
        │           └── assess_narrator_render_semantics
        ├── turn_runner_updates (continuity, memory, grounding rebuild, audit)
        └── session_lifecycle.save_current_session → SessionManager
```

**Alternate V1 path (headless):** `headless_scene_simulation.py` → `headless_turn_runner_wire.py` → same `turn_runner` loop without Streamlit UI.

**V2 production path (no V1 orchestration):**

```text
Launch-Holy-Grail-V2.bat / npm run app
  → HolyGrailRuntimeSupervisor
  → Python Domain Host (SessionRepository, DomainKernel)
  → localhost HTTP Domain API
  → DSH / Cordis (HgRoundOrchestrator, HgPhaseExecutors, HgContextBridge, HgTraceEmitter)
  → dsh-llm-deepseek provider
```

V2 **does not** import `turn_runner`, `model_client`, `app_turn_director`, or AutoGen agent construction at runtime.

---

## 3. Component classification

### A — Superseded runtime mechanism

| Component | V2 replacement |
|-----------|----------------|
| `turn_runner.py` + `turn_runner_*` | `HgRoundOrchestrator` + phase executors |
| `app.py` message/turn loop | `HolyGrailApplicationClient` + supervisor |
| `app_turn_director.py` | `ParticipationDecision` + Director phase executor |
| `app_turn_selector.py` | Participation policy (no AutoGen selector) |
| `model_client.py` | DSH `dsh-llm-deepseek` + `InferenceProfile` |
| `semantic_validation.py` (V1 LLM path) | Domain `validate_move` / `validate_director_decision` |
| `app_turn_prompting.py` / `prompt_topology_issue240.py` (character) | `continuity_context_projector` + `KnowledgeService` + `HgContextBridge` |
| `director_prompt_payload.py` (orchestration) | `prepare_director_context` manifest |
| `pending_forced_speaker` session flags | Request-scoped `forcedDesignation` |
| Streamlit runtime authority for routing | Domain API request contracts |
| V1 narrator render loop + semantic re-render | Post-commit `prepare_narrator_context` + single narrator inference |

### B — Reusable domain library (V2 imports today)

| Module | V2 consumer | Notes |
|--------|-------------|-------|
| `continuity_manager.py` + continuity_state* | `session_repository`, `kernel`, `session_setup` | Authoritative state |
| `session_manager.py` | `SessionRepository` | File persistence wrapper |
| `character_state_model.py` | memory, session | Character state |
| `character_loader.py` | `session_setup`, `setup_catalog` | **Card load only**; `create_agent` unused by V2 |
| `scene_template.py`, `scene_opener.py` | `session_setup` | Template/opener assets |
| `memory_layer.*` | `memory_write_policy`, `memory_retrieval` | Session memory |
| `response_validation*` | `kernel.validate_move` | Parse/validate moves |
| `perception_audibility*` | `kernel`, `memory_write_policy` | Perception filtering |
| `scene_grounding.py` | `continuity_context_projector` | Live rebuild/format |
| `canonical_compile_adapters.py` | `authored_knowledge` | Lore compile |
| `prompt_builders.build_narrator_render_prompt` | `kernel.prepare_narrator_context` | Narrator instruction formatter |
| `issue240_semantic_evaluation` | `kernel.commit_move` | Continuity normalization |
| `app_state_scene.py`, `continuity_setup_seam_v77` | `session_setup` | Scene apply |

### C — Unmigrated product capability (potential blockers)

| Capability | Evidence | Severity |
|------------|----------|----------|
| LLM-generated opening (`STREAMLIT_OPENING_MODE_GENERATED`) | `ui_sidebar_opening.py`, `bootstrap_composition` | Medium — V2 has minimal/custom only |
| Full template opener bootstrap (character opener LLM beats) | M9 deferred | Medium |
| Player character selection / user persona UI | V1 `session_lifecycle_load`, sidebar | Medium — V2 has `user_profile` API, limited UI |
| Per-role model/reasoning controls in UI | V1 sidebar + `model_client` | Low — V2 uses `cordis.yml` InferenceProfile |
| Narrator semantic assessment + re-render retry | `turn_runner_character_render`, `assess_narrator_render_semantics` | Low-Medium — V2 presentation is single-pass |
| Authored retrieval index + episodic select in prompts | `prompt_retrieval_assembly.py` | Low — V2 has session episodic + KnowledgeService; no vector index |
| Rich audit viewer UI | `audit_logger`, Streamlit audit panes | Low for product inference — ops/debug |

### D — Deprecated surface/plumbing

| Item | Role |
|------|------|
| `app.py` Streamlit entry | Deprecated production surface |
| `ui_sidebar_*`, `ui_chat` | V1-only UI |
| `app_state_runtime.py` (AutoGen CancellationToken) | V1 session glue |
| `headless_turn_runner_wire.py` | Headless V1 orchestration wire |

### E — Test/evidence asset

| Asset | Retain as |
|-------|-----------|
| `autogen_rp/python/tests/` (~154) | Legacy behavioral contracts; port or fence |
| `validation_runs/`, audit scenarios | Archival evidence |
| `governance/rp-app/*` | Architecture record |
| V2 `v2/tests/` + `v2/rp_runtime/tests/` | Primary CI contract |

### F — Unknown / needs investigation

| Item | Question |
|------|----------|
| Participation fairness heuristics beyond eligibility | Product-required or abandoned? — **No V2 gap found**; fairness = eligibility + participation policy |
| `progression_advisory` / anti-regression prefixes | Required in V2 Director context? — **Not ported**; classify as unmigrated advisory unless product requests |
| Beat-shift director hints | V1 director payload only — **deferred** |

---

## 4. AutoGen dependency inventory

| File | AutoGen surface | V2 transitively? | Notes |
|------|-----------------|------------------|-------|
| `character_loader.py` | `AssistantAgent`, `ChatCompletionClient` | Import path only | V2 calls `load_character_card` |
| `model_client.py` | `OpenAIChatCompletionClient`, agents | **No** | V1-only |
| `app_turn_director.py` | `TextMessage` | **No** | |
| `app_turn_rendering.py` | `TextMessage` | **No** | |
| `turn_runner_character_attempt.py` | `TextMessage` | **No** | |
| `semantic_validation.py` | `AssistantAgent` | **No** | |
| `audit_v2_llm.py` | `AssistantAgent` | **No** | Audit tooling |
| `scene_start_bootstrap.py` | `TextMessage`, `CancellationToken` | **No** | |
| `app_state_runtime.py` | `CancellationToken` | **No** | |

**No `GroupChat` / selector teams in `rp_app`.** V2 Node runtime uses DSH ephemeral agents, not Python AutoGen.

**Removal boundary:** AutoGen can leave the repo when (1) V1 `turn_runner` spine retired or fenced, (2) `character_loader.create_agent` split out, (3) audit/headless legacy paths migrated or archived, (4) vendored `autogen_rp/python/packages/*` no longer required by product CI.

---

## 5. Prompt-path inventory

| V1 path | Status | V2 equivalent |
|---------|--------|---------------|
| `prompt_builders.build_character_turn_prompt` | **Superseded** | `prepare_context` manifest lanes |
| `prompt_topology_issue240` | **Superseded** (character) | ContextAssembly + bridge |
| `director_prompt_payload` | **Superseded** | `prepare_director_context` |
| `prompt_grounding_assembly` | **Superseded** | `continuity_context_projector` → `scene_grounding` lane |
| Canon in `prompt_builders` JSON blocks | **Superseded** | `continuity_canon` lane |
| `prompt_retrieval_assembly` | **Unmigrated semantics** (index/episodic select) | Partial: KnowledgeService + session episodic memory lane |
| `prompt_builders.build_narrator_render_prompt` | **Reused formatter** | Still called from `kernel.prepare_narrator_context` |
| `scene_grounding.format_*` | **Reused formatter** | Called from projector |
| Retry/schema instructions in `prompt_builders` | **Superseded** | `inference_instruction` contribution + DSH agent config |
| V1 memory/world/preference JSON blocks | **Superseded** | MemoryService + KnowledgeService lanes |

---

## 6. Turn-runner parity matrix

| Responsibility | V1 | V2 replacement | Parity | Gap | Retirement condition |
|----------------|-----|----------------|--------|-----|---------------------|
| User ingress | `process_user_message` | Application client + `record_user_turn` | ✅ | — | V2 default UX only |
| Actor eligibility | `orchestration_helpers` | `eligible_actors` API | ✅ | — | V2 tests green |
| Forced speaker | `pending_forced_speaker` | `ParticipationDecision` + `detectForcedSpeaker` | ✅ | — | M5+ validated |
| Continuation | `resolve_continuation_override_actor` | `participation_policy.resolve_continuation_actor` | ✅ | — | V2 policy tests |
| Director selection | `choose_next_actor` LLM | Director phase executor | ✅ | Progression advisory not ported | Product sign-off on advisories |
| Multi-char sequencing | `turn_runner` loop | `HgRoundOrchestrator.runRound` | ✅ | — | Node generic-round tests |
| Validation/retry | `turn_runner_character_attempt` | Phase executor + Domain validate | ✅ | — | — |
| Commit | `turn_runner_updates` + continuity | `commit_move` | ✅ | — | — |
| Presence mutation | continuity `process_turn` | Same ContinuityManager | ✅ | — | — |
| Memory write | `app_memory_*` / memory_layer | `MemoryService` | ✅ | Cross-scope user-rel only | M10.2 scope |
| Knowledge promotion | V1 buckets | `KnowledgeService` M11.2 | ✅ | No V1 bucket migration | — |
| Narrator | render + semantic retry | post-commit narrator phase | ⚠️ partial | No semantic re-render | Explicit defer or port |
| Round completion | `turn_runner` end conditions | Orchestrator completion rules | ✅ | — | — |
| Trace/audit | `turn_runner_audit`, `audit_logger` | `HgTraceEmitter` + DSH sessions | ⚠️ partial | No V2 audit UI | Ops tooling separate |
| Session persistence | `SessionManager` | `SessionRepository` | ✅ | Still wraps V1 manager | Extract persistence later |

---

## 7. Director/selection retirement assessment

**Fully replaced:** hard forced speaker, continuation override, Director LLM selection path, eligibility floor, used-this-round tracking.

**Still in V1 only:** `progression_advisory`, `anti_regression_advisory`, beat-shift director hints — advisory prompt prefixes in `director_prompt_payload`. Not blocking inference correctness; **non-blocking** unless product mandates progression hints in V2 Director manifest.

**Fairness:** V1 "fairness" is implemented as eligibility + participation ordering, not a separate fairness engine. **No abandoned fairness mechanism blocks retirement.**

---

## 8. Narrator retirement assessment

| V1 behavior | V2 status |
|-------------|-----------|
| Post-commit presentation render | ✅ `prepare_narrator_context` + narrator phase |
| `build_narrator_render_prompt` | ✅ reused |
| `assess_narrator_render_semantics` + fallback re-render | ❌ not ported |
| UI chat insertion | ✅ `record_presentation` + `rp_history` |
| Audit of narrator validation | ⚠️ DSH trace only |

**Blocker assessment:** Narrator semantic re-render is **not a blocker** for V1 runtime deletion if product accepts single-pass presentation (documented deferral in `v2-narrator-orchestration.md`). Canon is unaffected.

---

## 9. Opening/bootstrap gap assessment

| V1 mode | V2 status | Product criticality |
|---------|-----------|---------------------|
| `minimal` | ✅ M9 | Core |
| `custom` | ✅ M9 + V2 Streamlit | Core |
| `template` + opener catalog | ⚠️ catalog exposed; full bootstrap deferred | Medium |
| `generated` (LLM opening) | ❌ not in V2 | Medium — convenience, not canon |
| `bootstrap_composition` / interpretation snapshot | ❌ V1/headless only | Low for V2 product |

**Prerequisite slice before full V1 delete:** either port `generated`/full template bootstrap to Domain Host **or** explicitly defer and document product exclusion.

---

## 10. Player/settings gap assessment

| V1 feature | V2 status |
|------------|-----------|
| Player character pick | V1 sidebar; V2 limited |
| User persona / preferred name | `user_profile` API (M11.2); minimal UI |
| Model provider | `cordis.yml` InferenceProfile | 
| Per-role model in UI | Not in V2 Streamlit |
| Scene template/options | ✅ catalog + create API |

**Blocker assessment:** Player character UX is **medium** — not required for multi-character AI-AI rounds; required for finished player-facing product. Does not require preserving V1 `turn_runner`.

---

## 11. Audit/debug gap assessment

| Class | V1 | V2 |
|-------|-----|-----|
| Execution evidence | `audit_logger`, turn JSON | DSH inference sessions + `HgTraceEmitter` |
| Domain audit | continuity snapshots in audit | Domain `continuity_version`, commit IDs |
| Operator UI | Streamlit audit panes | None |
| Dev tooling | headless simulations | V2 Node tests + mock LLM |

**Blocker assessment:** Audit **UI** does **not** block V1 runtime retirement. Ops can use DSH logs and V2 events. Preserve audit **artifacts** as evidence archive.

---

## 12. Memory/knowledge V1 dependency assessment

| V1 module | V2 usage | Action |
|-----------|----------|--------|
| `memory_layer.writes/retrieval` | MemoryService | **extract/rehome** |
| `app_memory_summary` | `memory_write_policy` | **extract/rehome** |
| `build_memory_buckets` | Superseded | **remove** with V1 runtime |
| `extract_user_preferences` | Superseded by explicit user_profile | **remove** |
| `prompt_retrieval_assembly` | Not used by V2 | **retain as test/evidence** until episodic/index decision |
| `canonical_compile_adapters` | KnowledgeService | **extract/rehome** |

M10/M11 semantics migrated. Remaining imports are **domain helpers**, not V1 runtime orchestration.

---

## 13. Session/persistence dependency assessment

`SessionManager` is **reusable persistence infrastructure** with minimal Streamlit coupling (no direct `st` imports in `session_manager.py`).

| Concern | Assessment |
|---------|------------|
| create/load/save | Used by V2 `SessionRepository` |
| Index/metadata | Shared file layout |
| V1-specific metadata keys | Coexist with `v2_host_state` |
| Extraction needed? | **Yes, eventually** — rename/rehome to `v2/domain/persistence/` |
| Blocks V1 orchestration retirement? | **No** — can remain while turn_runner deleted |

---

## 14. Final package/directory recommendation

**Recommended end-state: Option C variant**

```text
v2/
  domain_api/          # Domain Host kernel, services, HTTP (permanent)
  domain/              # extracted framework-neutral domain library (future)
  rp_runtime/          # DSH/Cordis/Node orchestration (permanent)
  ui/                  # V2 Streamlit shell (permanent)
  tests/
governance/
legacy/                # archived V1 orchestration + headless wires (post-retirement)
data/                  # character cards, templates (shared assets)
```

**Phased path:**

1. Extract reusable Python from `rp_app/` → `v2/domain/` (no behavior change).
2. Retire `turn_runner` spine to `legacy/v1-orchestration/`.
3. Remove `autogen_rp/python/packages/` vendored AutoGen when nothing imports it.
4. Rename `autogen_rp` → eliminate from core naming (archive or delete tree).

Do **not** big-bang rename in M12.

---

## 15. Test-retention strategy

| Class | Action |
|-------|--------|
| `v2/tests/*.py` | **Retain** — primary Python contract |
| `v2/rp_runtime/tests/*.mjs` | **Retain** — primary orchestration contract |
| V1 continuity/validation/perception tests | **Port** key cases already in V2; retain remainder on domain helpers until extraction |
| V1 `test_turn_runner_*`, `test_app_*` integration | **Retire with mechanism** or move to `legacy/tests/` |
| AutoGen package tests under `packages/` | **Retire** when dependency removed |
| Headless simulation tests | **Archive** as evidence or rewrite against V2 harness |

**Rule:** behavioral contracts worth keeping must anchor to **public V2 boundaries** (Domain API + round orchestrator), not `turn_runner` internals.

---

## 16. Scenario/audit evidence retention

| Asset | Retention |
|-------|-----------|
| `validation_runs/issue*/` | Archival fixtures — implementation-independent |
| Audit JSON from V1 sessions | Historical evidence — do not require V1 runtime to read |
| Progression scenario manifests | Reference for future parity — not CI blockers |
| V2 Node round tests | Primary ongoing regression |

No new RP scenarios required for M12.

---

## 17. Comprehensive retirement matrix (primary deliverable)

| Component | Category | V2 replacement | Parity | Consumers | Removal condition | Action |
|-----------|----------|----------------|--------|-----------|-----------------|--------|
| `app.py` | D | V2 `npm run app` | ✅ UX | Streamlit | V2 default only + docs | remove |
| `turn_runner.py` | A | HgRoundOrchestrator | ✅ | app, headless | V2 round CI + legacy fenced | remove |
| `model_client.py` | A | dsh-llm-deepseek | ✅ | app, headless | No production import | remove |
| `app_turn_director.py` | A | Participation + Director phase | ✅ | turn_runner | Policy tests green | remove |
| `app_turn_prompting.py` | A | ContextAssembly | ✅ | turn_runner | Manifest parity | remove |
| `prompt_topology_issue240.py` | A | projector + KnowledgeService | ✅ | app | V2 context tests | remove |
| `director_prompt_payload.py` | A | prepare_director_context | ⚠️ advisories | turn_runner | Product on advisories | remove |
| `semantic_validation.py` | A | Domain validation | ✅ | turn_runner | — | remove |
| `continuity_manager.py` | B | same | ✅ | V2 domain_api | Extract first | extract/rehome |
| `session_manager.py` | B | SessionRepository | ✅ | V2 | Extract persistence | extract/rehome |
| `character_loader.py` | B | card load | ✅ | V2 setup | Split create_agent | extract/rehome |
| `scene_grounding.py` | B | projector | ✅ | V2 | — | extract/rehome |
| `response_validation*.py` | B | kernel validate | ✅ | V2 | — | extract/rehome |
| `memory_layer.*` | B | MemoryService | ✅ | V2 | — | extract/rehome |
| `prompt_builders.py` | mixed | partial reuse | ⚠️ | V1 + narrator | Split narrator helper | extract/rehome |
| `prompt_retrieval_assembly.py` | C | partial | ❌ index | V1 only | Episodic policy | migrate behavior first |
| `bootstrap_composition.py` | C | M9 minimal | ⚠️ | V1/headless | Opening policy | migrate behavior first |
| `ui_sidebar_*` | D | v2/ui | ⚠️ settings | V1 | V2 settings parity | remove |
| `audit_logger.py` | E | HgTraceEmitter | ⚠️ UI | V1 | Ops tooling | retain as evidence |
| `headless_turn_runner_wire.py` | D | V2 tests | ✅ | scripts | Legacy fence | remove |
| Vendored `packages/autogen-*` | A/D | DSH | ✅ | V1 | Zero imports | remove |

---

## 18. Real blockers to V1 runtime deletion

Ranked by product importance:

1. **Domain library extraction** — V2 still `sys.path`-imports `rp_app`; deleting tree breaks V2. **Architectural blocker**, not product behavior.
2. **Opening/bootstrap parity** — `generated` mode and full template bootstrap not in V2. **Medium product blocker** if users expect those modes.
3. **Player character / settings UX** — V2 UI incomplete vs V1 sidebar. **Medium** for player-facing product.
4. **Legacy CI dependency** — ~154 V1 tests and headless scripts assume `turn_runner`. **Process blocker**.
5. **Narrator semantic re-render** — **Low**; explicitly deferred.
6. **Authored retrieval index in prompts** — **Low**; KnowledgeService + episodic partial cover.
7. **Audit viewer UI** — **Non-blocker** for runtime retirement.

---

## 19. Non-blocking V1 leftovers

- Vendored AutoGen monorepo packages (not used by V2)
- `ReplayChatCompletionClient` / V1 mock clients (test-only)
- Streamlit audit panes
- `progression_advisory` / anti-regression prompt prefixes
- V1 regex `user_preferences` (superseded M11.2)
- `build_memory_buckets` save-time aggregation
- README references to `streamlit run app.py` (doc drift)
- `autogen_rp/python/samples/*` (upstream samples)

---

## 20. AutoGen removal end-state

Before removing AutoGen from the repository:

1. No V2 production import of AutoGen types (already true for orchestration).
2. `character_loader` split — card I/O framework-neutral.
3. V1 `turn_runner` + `model_client` removed or in `legacy/`.
4. Headless wires either deleted or run only via `legacy` target.
5. V1 behavioral tests ported to V2 boundaries or archived.
6. `pyproject`/requirements no longer list `autogen-*` for product install.
7. Vendored `autogen_rp/python/packages/` removed from product CI path.

---

## 21. Recommended phased retirement sequence

| Phase | Focus | Retires | Gate |
|-------|-------|---------|------|
| **M12.1** | Split `character_loader`; framework-neutral card I/O | AutoGen from shared loader | V2 93+51 green |
| **M12.2** | Extract `v2/domain/` package from `rp_app` helpers | `sys.path` rp_app injection | Import boundary tests |
| **M12.3** | Fence `legacy/v1-orchestration/`; move turn_runner spine | app turn loop from default CI | Legacy test target explicit |
| **M12.4** | Delete fenced V1 orchestration after legacy CI port | turn_runner, model_client, app.py | No default launch to V1 |
| **M12.5** | Opening/bootstrap parity OR explicit product deferral | bootstrap_composition V1 path | Governance decision |
| **M12.6** | Player/settings UX on V2 UI | ui_sidebar_* | UX sign-off |
| **M12.7** | Remove vendored AutoGen packages | packages/autogen-* | Zero imports |
| **M12.8** | SessionManager rehome + `autogen_rp` tree deletion | rp_app runtime shell | Domain lib in v2/domain |

---

## 22. First bounded cutover slice (exactly one)

### **M12.1 — Framework-neutral character card I/O split**

**Why this slice first:**

- Removes AutoGen from the **only** `rp_app` module V2 touches that imports `AssistantAgent`
- Does not delete turn_runner yet (low blast radius)
- Enables clean `v2/domain/characters/` package in M12.2
- V2 already uses `load_character_card` only — behavior unchanged
- Strong regression evidence: M9 session setup + catalog tests

**Scope:**

- Extract card loading/validation to framework-neutral module (e.g. `v2/domain/character_cards.py` or split `character_loader.py`)
- Move `create_agent` / AutoGen factory to `legacy/v1_autogen_agents.py`
- Update V2 imports to neutral module
- Gate: V2 93 Python + 51 Node green; V1 card tests pass

**Does not include:** turn_runner deletion, AutoGen package removal, opening parity, UI migration.

---

## 23. Challenge/refinement

| Question | Verdict |
|----------|---------|
| Deleting implementation vs behavior? | Plan deletes **mechanisms**; domain semantics preserved via V2 services |
| V2 replacements validated? | **Yes** for orchestration, memory, knowledge, context |
| Helpers framework-neutral? | **Not yet** — extraction required before tree delete |
| Preserving obsolete code due to imports? | **Yes risk** — M12.2 addresses |
| Prompt builders superseded? | Character/director **yes**; narrator format **reused intentionally** |
| Subtle V1-only behavior? | Progression advisories, narrator semantic retry, generated opening |
| AutoGen still needed? | **V1 orchestration only** |
| Tests mistaken for deps? | V1 suite is large but **fenceable** |
| Audit UI blocking? | **No** |
| First slice simplifies repo? | **Yes** — first AutoGen-free shared import |
| Final package clean? | `v2/domain/` + eliminate `autogen_rp` naming |

---

## 24. Architecture verdict

**Retirement plan established with focused unresolved blockers**

V2 parity is **sufficient for orchestration retirement planning**. Remaining blockers are **library packaging**, **opening/bootstrap policy**, and **player UX** — not core round correctness.

---

## 25. Next recommended implementation slice

**M12.1 — Framework-neutral character card I/O split** (same as §22). Do not implement without Governance review.

---

## 26. Retirement gates (reference)

```text
V2 behavior validated
→ no production V2 consumer of old path
→ relevant behavioral tests preserved
→ old implementation removed or fenced to legacy/
→ dependency/package cleanup
→ docs/launch references updated
→ full validation
```

No compatibility aliases without explicit removal condition.
