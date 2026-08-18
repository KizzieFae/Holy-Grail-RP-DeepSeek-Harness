# V2 Director + Character Orchestration — Implementation Report

**Status:** Completed (authorized multi-role orchestration slice)  
**Date:** 2026-03-17  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Boundary prototype anchor:** `537419b`  
**Implementation HEAD:** (see §15 after commit)

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `537419bd427fff2b71160e0a9aefccac69993d72` |
| `origin/main` | aligned at slice start |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 implementation |
| Previous prototype | green (6 Python + 2 Node tests) before expansion |

---

## 2. Runtime architecture changes

### Promoted to permanent V2 architecture

| Component | Role |
|-----------|------|
| `v2/rp_runtime/src/plugins/hg-rp-runtime/service.mjs` | `HolyGrailRpRuntime` Cordis Service — RP orchestration |
| `v2/rp_runtime/src/plugins/hg-rp-runtime/events.mjs` | HG execution-event helpers and taxonomy |
| `v2/rp_runtime/src/bootstrap.mjs` | Runtime stack bootstrap |
| `v2/rp_runtime/src/lib/inference-utils.mjs` | Shared inference helpers |
| `v2/rp_runtime/src/lib/domain-api-client.mjs` | Domain API HTTP client with boundary metrics |

### Domain API extensions (permanent contract)

| Operation | Endpoint |
|-----------|----------|
| `start_round` | `POST /v1/rounds/start` |
| `prepare_director_context` | `POST /v1/director/context/prepare` |
| `validate_director_decision` | `POST /v1/director/decisions/validate` |
| Character operations | unchanged paths, extended with `hg_round_id` |

### Superseded and removed

| Component | Replacement |
|-----------|-------------|
| `character-inference-slice.mjs` | `HolyGrailRpRuntime.runCharacterInference()` |
| `run-prototype.mjs` | runtime tests + `HolyGrailRpRuntime` |
| `src/domain-api-client.mjs` (root) | `src/lib/domain-api-client.mjs` |

---

## 3. Director implementation

- **Context:** `prepare_director_context` returns scene state + `director_scratch` + inference instruction. No `character_private` contributions.
- **Validation:** `validate_director_decision` uses Holy Grail `parse_director_decision` with cast as `participant_names` / `available_actors`.
- **Inference:** ephemeral DSH agent per director attempt; mock LLM returns structured JSON.
- **Events:** `hg/director-proposed`, `hg/director-rejected`, `hg/director-accepted` on scene session.

---

## 4. Character implementation

- Retains boundary-prototype behavior: manifest → ephemeral inference → validate → commit.
- **Context:** includes `character_private` contribution (isolation marker); excludes `director_scratch`.
- **Commit:** uses validated `director_decision` from director phase (not stub).
- **Retry:** invalid character move rejected with `hg/move-rejected`, retry on next mock response.

---

## 5. Session topology evidence

| Session | Purpose |
|---------|---------|
| Scene session (`hg-scene-{hg_scene_id}`) | Correlation anchor; all `hg/*` execution events |
| Director inference session (`hg-inf-director-*`) | Ephemeral; disposed after director step |
| Character inference session (`hg-inf-character-*`) | Ephemeral; separate from director |

Evidence: integration test confirms three distinct session IDs. Scene session holds correlated trace; inference sessions hold only DSH turn/step/assistant events for that role.

---

## 6. Context-isolation proof

| Requirement | Evidence |
|-------------|----------|
| Director excludes character-private | Python `test_director_context_excludes_character_private`; Node `context isolation` test |
| Character excludes director scratch | Same tests — `director_scratch` ∉ character kinds |
| Separate characters isolatable | Per-character `character_private_secrets` in fixture; manifests scoped per `character_id` |
| Scene correlates both roles | `hg/round-started` → director events → move events share `hg_round_id` + `dsh_scene_session_id` |

---

## 7. HG event model

Log-only events on scene session:

- `hg/round-started`
- `hg/director-proposed` / `hg/director-rejected` / `hg/director-accepted`
- `hg/move-proposed` / `hg/move-rejected` / `hg/move-committed`

Correlation fields: `hg_scene_id`, `hg_round_id`, `inference_id`, `role`, `character_id`, `attempt_index`, `manifest_id`, `dsh_scene_session_id`, `director_inference_session_id` / `character_inference_session_id`, `continuity_turn_index`, `domain_commit_id`.

---

## 8. Full Director → Character sequence

```text
1. POST /v1/scenes (or reuse) → POST /v1/rounds/start
2. Create scene DSH session; append hg/round-started
3. POST /v1/director/context/prepare → ephemeral director inference
4. append hg/director-proposed → POST /v1/director/decisions/validate
5. On accept: hg/director-accepted with selected_character_id
6. POST /v1/context/prepare (selected character) → ephemeral character inference
7. append hg/move-proposed → POST /v1/moves/validate
8. On accept: POST /v1/moves/commit (with director_decision) → hg/move-committed
```

---

## 9. State-authority proof

- Director validation rejection leaves `turn_counter=0`, no `hg/move-committed`.
- Character proposal without commit leaves continuity unchanged (inherited from boundary tests).
- Only `ContinuityManager.process_turn` via `commit_move` increments turn counter.
- DSH `hg/*` events are log-only execution evidence.

---

## 10. Boundary efficiency observations

Successful Director → Character round (measured via `boundary_metrics`):

| Call | Typical count |
|------|---------------|
| `createScene` | 1 |
| `startRound` | 1 |
| `prepareDirectorContext` | 1 |
| `validateDirectorDecision` | 1 |
| `prepareCharacterContext` | 1 |
| `validateMove` | 1 |
| `commitMove` | 1 |
| **Total** | **~7 HTTP calls** |

Payload sizes: manifests ~0.5–1.5 KB each; move/decision JSON ~0.3–0.8 KB. HTTP overhead acceptable for prototype; no material blocking observed. Repeated adapter registration per ephemeral inference adds minor DSH setup cost.

---

## 11. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | **8 passed** |
| `npm test` (v2/rp_runtime) | **7 passed** |
| `pytest tests -m "not llm"` | **1361 passed, 1 failed** (pre-existing presence test) |

---

## 12. Clean-V2 review

| Classification | Components |
|----------------|------------|
| **Permanent** | Domain API contract/kernel, `HolyGrailRpRuntime`, event helpers, lib utilities |
| **Promoted** | Orchestration moved from prototype script into Cordis Service |
| **Still transitional** | HTTP transport, fixture store, mock LLM adapter |
| **Removed** | `character-inference-slice.mjs`, `run-prototype.mjs`, root `domain-api-client.mjs` |
| **Test-only** | Mock LLM, integration test harness |

---

## 13. Challenge / refinement

| Question | Finding |
|----------|---------|
| DSH orchestrating RP work? | **Yes** — `runDirectorCharacterRound` sequences director then character with scene-session correlation |
| Cordis plugin simplifies design? | **Yes** — single service vs scattered scripts |
| Boundary too chatty? | **Moderate** — 7 calls acceptable for slice; batching possible later |
| Scene identity preserves isolation? | **Yes** — separate ephemeral inference sessions |
| Ephemeral agents behave correctly? | **Yes** — distinct session IDs, no cross-inheritance |
| HG events useful? | **Yes** — scene session reconstructs full round trace |
| Replacing V1 structurally? | **Beginning** — orchestration in DSH service, domain in Python |
| Narrator fit naturally? | **Yes** — same manifest + ephemeral inference pattern |
| Second character fit? | **Yes** — director selects; character slot is parameterized |
| Prototype clutter? | **Reduced** — superseded scripts removed |

---

## 14. Architecture verdict

**Architecture validated with refinements**

Multi-role orchestration works with scene-session correlation + ephemeral inference sessions. HTTP transport remains adequate. Future: formal Cordis `SessionEventMap` plugin registration for `hg/*` types when persistence is needed.

---

## 15. Repository state

| Field | Value |
|-------|-------|
| Commit | `2135ef7a602444c84123de831ad25ff3e3df4bef` |
| Branch | `main` |
| Push status | pushed to `origin/main` |
| Working tree | clean |

---

## 16. Next recommended slice (Governance review required)

**Add Narrator as a third ephemeral inference role** in the same round trace (presentation-only, no continuity authority), proving three-role orchestration before multi-character cast loops.

Do not implement without Governance authorization.
