# V2 Boundary Prototype — Implementation Report

**Status:** Completed (authorized narrow vertical slice)  
**Date:** 2026-03-17  
**Baseline anchor:** `12489a93146c9673a66518d7b3cc2a3ec02fba3b`  
**Architecture decision:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Implementation HEAD:** (see §12 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `2ee410321f19e57c4579821ce590f701ccf2eedf` |
| `origin/main` | aligned at slice start |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 implementation/bootstrap |
| DSH before slice | not installed (confirmed) |

---

## 2. DSH installation

**Upstream npm (2026-03-17):** unchanged from architecture evaluation.

| Package | Pinned version |
|---------|----------------|
| `@deepseek-ai/cordis` | `4.0.1` |
| `@deepseek-ai/cordis-plugin-loader` | `1.0.2` |
| `@deepseek-ai/dsh-agent` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-agent-loop` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-agent-loop-testkit` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-llm` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-session` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-session-persistence` | `0.1.0-rc.7` |
| `@deepseek-ai/dsh-system-prompt` | `0.1.0-rc.7` |

Pins recorded in `v2/dsh-pins.toml` and `v2/rp_runtime/package.json`.

**Composition:** programmatic minimal stack via `mountAgentLoopTestDependencies` + `AgentLoop` — no bash, editor, filesystem, sandbox, or coding-agent tools. Reference `cordis.yml` documents the spine only.

**Mock LLM:** `HgMockLlmAdapter` (`v2/rp_runtime/src/mock-llm-adapter.mjs`) registered on provider route `hg-mock`.

---

## 3. Domain API contract

**Transport-neutral contract:** `v2/domain_api/contract.py`

| Operation | Input | Output |
|-----------|-------|--------|
| Context prepare | `hg_scene_id`, `inference_id`, `character_id`, `role`, `turn_index`, `attempt_index` | `PromptContributionManifest` with provenance-first contributions |
| Validate move | proposed move + correlation ids | `accepted` / `validation_class` / `reason` / `retryable` / `normalized_move` |
| Commit move | validated move + `expected_turn_index` anchor | `committed` / `continuity_turn_index` / `domain_commit_id` |

**Prototype transport (replaceable):** HTTP localhost (`v2/domain_api/http_transport.py`)

> The Domain API contract is architectural; the prototype transport is replaceable.

---

## 4. Implemented architecture

| Component | Classification | Responsibility |
|-----------|----------------|----------------|
| `v2/domain_api/contract.py` | **V2 permanent** | Transport-neutral types |
| `v2/domain_api/kernel.py` | **V2 permanent** | Authoritative prepare/validate/commit via `ContinuityManager.process_turn` |
| `v2/domain_api/fixture_store.py` | **prototype/transitional** | In-memory scenes; replace with real session store |
| `v2/domain_api/http_transport.py` | **prototype/transitional** | HTTP binding; replace with gRPC/IPC/plugin bridge |
| `v2/rp_runtime/src/character-inference-slice.mjs` | **prototype/transitional** | Orchestrates one ephemeral inference; becomes RP runtime plugin |
| `v2/rp_runtime/src/mock-llm-adapter.mjs` | **test/prototype** | Deterministic LLM; remove when real provider wired |
| `v2/rp_runtime/src/domain-api-client.mjs` | **prototype/transitional** | HTTP client; replace with transport abstraction |
| `v2/rp_runtime/cordis.yml` | **documentation** | Documents minimal spine |

**Removal conditions:**

- `fixture_store.py` / `http_transport.py` → when Domain API is served through production transport and real scene persistence.
- `character-inference-slice.mjs` → when extracted into a Cordis plugin with Director/Narrator orchestration.
- `mock-llm-adapter.mjs` → when real DeepSeek (or other) adapter is integrated behind the same boundary.

---

## 5. End-to-end prototype flow

```text
1. DSH creates ephemeral inference session (SessionId)
2. DSH → POST /v1/context/prepare → PromptContributionManifest
3. DSH registers manifest contributions via agent.ctx.systemPrompt.context()
4. Mock LLM streams canonical v2 JSON move
5. DSH appends hg/move-proposed (log-only)
6. DSH → POST /v1/moves/validate → Python parse + validate_bot_response
7. On reject: hg/move-rejected, retry with next mock response
8. On accept: DSH → POST /v1/moves/commit → ContinuityManager.process_turn
9. DSH appends hg/move-committed with domain_commit_id + continuity_turn_index
```

---

## 6. State authority proof

| Requirement | Evidence |
|-------------|----------|
| DSH cannot create truth | `test_proposal_without_commit_does_not_mutate_continuity`; Node test `DSH-only proposal does not commit` — turn_counter stays 0 |
| Validation precedes commit | Invalid beats rejected before `process_turn`; `test_validation_rejects_invalid_before_commit` |
| Commit via HG authority | `test_commit_uses_authoritative_continuity_path` calls `ContinuityManager.process_turn` |
| Rejection traceable | `hg/move-rejected` events in DSH session without continuity mutation |
| Context provenance | `test_prepare_context_preserves_provenance`; manifest contributions carry `source_kind`, `knowledge_ids`, `provenance` |

---

## 7. Traceability proof

Correlation fields shared across boundary:

- `hg_scene_id`, `inference_id`, `attempt_index`, `character_id`
- `manifest_id` (context), `continuity_turn_index`, `domain_commit_id` (after commit)
- `dsh_session_id` on `hg/move-committed`

Cross-boundary test demonstrates: rejected attempt 0 visible in DSH log; attempt 1 commits; Python `turn_counter` and `committed_move_count` increment only after commit.

---

## 8. Validation

| Suite | Command | Result |
|-------|---------|--------|
| Domain API authority | `pytest v2/tests` | 6 passed |
| DSH boundary integration | `cd v2/rp_runtime && npm test` | 2 passed |
| Core non-LLM regression | `pytest autogen_rp/python/tests` (excl. LLM) | see §12 |

Known pre-existing failure (`test_descriptive_exit_updates_authoritative_presence_state`) may remain.

---

## 9. Clean-V2 review

No V1 code removed. No permanent `legacy_bridge` naming. DSH sessions represent execution history only; Python `ContinuityManager` remains sole commit authority.

Duplicate orchestration avoided: prototype runner is explicitly transitional, not parallel to `turn_runner`.

---

## 10. Challenge / refinement

| Question | Finding |
|----------|---------|
| DSH reduced to LLM proxy? | **No** — validate/commit/context are Python; DSH assembles and traces |
| Boundary too chatty? | **Acceptable for slice** — 3 HTTP calls per attempt; batching possible later |
| Context assembly deterministic? | **Yes** — manifest from fixture state; contributions registered explicitly |
| Model-visible contributions explainable? | **Yes** — manifest provenance + DSH systemPrompt.context names |
| DSH session leaked into domain? | **No** — scene state only changes via commit endpoint |
| Awkward TS/Python glue? | **Minor** — HTTP client is prototype-only; contract is clean |
| Director/Narrator support? | **Plausible** — same manifest pattern per role slot |
| One DSH session per scene? | **Still plausible** — prototype creates scene + inference sessions; scene session is placeholder for topology proof |
| Pluginization cleaner than V1? | **Yes** — clear seam vs monolithic turn_runner |
| Transitional clutter? | **Low** — fixture store + HTTP transport clearly marked |

---

## 11. Architecture verdict

**Architecture validated with refinements**

The boundary hypothesis survives implementation. Refinements identified:

1. Mock adapter must return full `resolveModel` metadata (`provider`, `id`, `context`) per DSH contract.
2. `hg/*` session events work at runtime without a registered plugin in this slice; production should register a Cordis plugin merging `SessionEventMap` for type safety.
3. HTTP transport should not survive beyond the next slice — consider in-process Python SDK or gRPC for lower latency.

---

## 12. Repository state

(Filled at commit time.)

---

## 13. Next step (requires Governance review)

**Authorized next slice (not implemented here):** Register Holy Grail Domain API as a formal Cordis-facing service plugin and replace HTTP with an in-process or SDK transport while keeping the same contract — then add a second ephemeral inference slot (Narrator **or** Director decision) to prove multi-role orchestration without persistent per-character DSH agents.
