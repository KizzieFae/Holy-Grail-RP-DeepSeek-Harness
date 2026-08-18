# V2 Real DeepSeek Provider Integration — Implementation Report

**Status:** Completed (production inference substrate validation slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**ParticipationDecision anchor:** `baf507e`  
**Implementation HEAD:** (recorded in commit message)

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `baf507e` |
| Assigned workflow weight | standard |
| Effective workflow weight | full |
| Bootstrap profile | full V2 implementation |
| Pre-slice validation | 37 Python + 23 Node tests green |

---

## 2. DSH provider architecture

**Packages (pinned `0.1.0-rc.7` unless noted):**

| Package | Role |
|---------|------|
| `@deepseek-ai/dsh-llm` | `LlmRuntime`, `LlmAdapter`, `registerAdapter`, streaming `StreamChunk` protocol |
| `@deepseek-ai/dsh-llm-deepseek` | Official DeepSeek adapter — provider route `deepseek-official` |
| `@deepseek-ai/dsh-agent-loop` | Ephemeral agent creation, `prepareCall`, `request/header` logging |
| `@deepseek-ai/dsh-session` | Durable inference session events (`assistant/chunk`, `assistant/message`, `turn/end`) |
| `@deepseek-ai/cordis` | Service composition |

**Configuration mechanism:**

- Plugin `apply(ctx, config)` from `@deepseek-ai/dsh-llm-deepseek`
- API key via `apiKeyEnv` (default `DEEPSEEK_API_KEY`) resolved from environment per request
- Models: pass-through wire ids (`deepseek-v4-flash`, `deepseek-v4-pro`)
- Reasoning: adapter-owned efforts `off|low|high|max`; serialized as DeepSeek `reasoning_effort` / `thinking.type`
- Streaming: SSE via `eventsource-parser`; `usage` precedes `finish`
- Retry policy: registered with adapter; execution optional via `dsh-llm-retry` (not mounted in V2 prototype)

**No parallel Holy Grail HTTP client.** V1 `model_client.py` remains untouched.

---

## 3. V2 provider configuration seam

**Permanent:** `v2/rp_runtime/src/lib/inference-profile.mjs`

```text
InferenceProfile
  kind: mock | dsh
  provider
  model
  reasoningEffort?   (dsh only)
  temperature?
  maxTokens?
```

- `mockInferenceProfile()` — test-only deterministic adapter
- `deepseekInferenceProfile(overrides)` — production DeepSeek default (`deepseek-v4-flash`, `reasoningEffort: low`)
- `resolveInferenceProfile(runtimeConfig, callProfile)` — per-call resolution
- `agentOptionsFromProfile(profile)` — maps to DSH `AgentOptions` without role coupling

**Runtime mount:** `createHolyGrailRpContext({ inference: { mountDeepSeek: true, deepseek: {...} } })`

Dynamic import of `@deepseek-ai/dsh-llm-deepseek` keeps mock-only tests free of provider package load.

---

## 4. Real inference proof

**Path:** `runCharacterInference()` → `prepareCharacterContext()` → `_runEphemeralInference({ modelProfile })` → DSH agent loop → `deepseek-official` adapter → DeepSeek API → Python `validateMove` / optional `commitMove`.

**Controlled slice:** single Character structured-move inference with minimal fixture (Alice, one scene).

**Live test:** `v2/rp_runtime/tests/real-inference.test.mjs` (requires `DEEPSEEK_API_KEY`).

---

## 5. Reasoning behavior

- Configured via `reasoningEffort` on `InferenceProfile` → DSH `request/header` → DeepSeek wire
- `low` used for integration test (faster/cheaper than default `high`)
- Reasoning blocks: separate `reasoning-delta` chunks → `reasoning` content blocks in `assistant/message`
- Trace field: `inference_trace.reasoning_text` (may be empty when effort is low/off)
- Reasoning passback: adapter-owned per DeepSeek thinking-mode rules (tool-call turns only)

---

## 6. Streaming behavior

Observed DSH lifecycle (via `inference_trace.stream`):

```text
request/header
  → assistant/chunk (block-start, text-delta, [reasoning-delta], usage, finish)
  → assistant/message
  → turn/end
```

Fields: `text_delta_count`, `reasoning_delta_count`, `usage`, `finish`.

---

## 7. Traceability proof

**DSH/provider evidence** (`extractInferenceTrace` in `inference-trace.mjs`):

| Field | Source |
|-------|--------|
| provider, model, reasoning_effort | `request/header` |
| manifest_id, contribution_ids | Domain API manifest correlation |
| stream summary | `assistant/chunk` events |
| reasoning_text, assistant_text | Assembled message |
| usage | `usage` chunk or `assistant/message.usage` |
| finish / failure | Terminal chunk or `turn/end` |

**Holy Grail domain evidence** (separate):

| Field | Source |
|-------|--------|
| proposed_move | Python validation input |
| validation_class, reason | Domain API |
| domain_commit_id | `commitMove` only |

**Scene events:** `hg/inference-failed` (provider failure), `hg/move-proposed`, `hg/move-committed`.

---

## 8. Provider failure semantics

**Test:** `provider-failure.test.mjs` — `apiKeyEnv: HG_TEST_MISSING_DEEPSEEK_KEY` (unset).

| Guarantee | Evidence |
|-----------|----------|
| No domain mutation | `turn_counter` unchanged |
| Structured failure | `provider_failure.code === MISSING_CREDENTIAL` |
| DSH records failure | `hg/inference-failed` scene event |
| No commit attempted | `committed === false`, `domain_commit_id === null` |

---

## 9. Mock/real separation

| Path | When | Classification |
|------|------|----------------|
| `HgMockLlmAdapter` | `profile.kind === 'mock'` (default) | **test-only** |
| `@deepseek-ai/dsh-llm-deepseek` | `profile.kind === 'dsh'` + `mountDeepSeek: true` | **permanent production** |

All existing deterministic tests unchanged (mock default). Real provider opt-in only.

---

## 10. Future role/model routing readiness

`_runEphemeralInference` accepts `modelProfile` per call. Role orchestration does not hard-code provider/model.

Future shape (not implemented):

```text
run inference(role=director, modelProfile=directorProfile)
run inference(role=character, modelProfile=characterProfile)
```

`agentOptionsFromProfile` already supports per-call provider/model/reasoningEffort.

---

## 11. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 37 passed |
| `npm test` (`v2/rp_runtime`) | **25 passed** (23 deterministic + 1 provider failure + 1 live DeepSeek) |
| Live inference | Passed with local `DEEPSEEK_API_KEY` |

---

## 12. Component classification

| Component | Class |
|-----------|-------|
| `inference-profile.mjs` | **permanent** |
| `inference-trace.mjs` | **permanent** |
| `mount-deepseek-provider.mjs` | **permanent** |
| `@deepseek-ai/dsh-llm-deepseek` dependency | **permanent** |
| `HgMockLlmAdapter` | **test-only** |
| `hg/inference-failed` event | **permanent** |
| HTTP Domain API transport | **transitional** |

**Not introduced:** parallel model client, V1 AutoGen assumptions, persistent provider flags, secrets in repo.

---

## 13. Architecture verdict

**Validated with refinements** — real DeepSeek inference flows through DSH's native adapter; mock remains test-only; provider failure is isolated from domain truth; per-role model profiles are structurally ready.

---

## 14. Deferred

- Per-role model routing policy
- `dsh-llm-retry` plugin mounting
- Streamlit / UI streaming
- OpenRouter or additional providers
- Full round (Director/Narrator) on real provider (Character slice sufficient for boundary proof)
