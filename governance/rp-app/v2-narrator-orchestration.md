# V2 Narrator Orchestration — Implementation Report

**Status:** Completed (three-role basic round slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**Director + Character anchor:** `193c768`  
**Implementation HEAD:** `8dd458c`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `193c76863f07973e0e700bb19d0d9e1615c9171a` |
| `origin/main` | aligned at slice start |
| Assigned workflow weight | standard |
| Effective workflow weight | **full** |
| Bootstrap profile | full V2 implementation |
| Previous slice | green (8 Python + 7 Node tests) before Narrator expansion |

---

## 2. Runtime architecture changes

### Promoted / refined permanent V2 architecture

| Component | Role |
|-----------|------|
| `HolyGrailRpRuntime._runEphemeralInference` | Shared ephemeral inference substrate (all roles) |
| `HolyGrailRpRuntime._correlation` | Shared scene-event correlation helper |
| `HolyGrailRpRuntime._runNarratorPresentation` | Narrator-specific presentation phase after commit |
| `prepare_narrator_context` | Domain API operation for presentation-only manifest |

### Domain API extensions (permanent contract)

| Operation | Endpoint |
|-----------|----------|
| `prepare_narrator_context` | `POST /v1/narrator/context/prepare` |

New `SourceKind`: `committed_move` — authoritative accepted move for presentation.

### Removed

None in this slice (no superseded V2 prototype paths replaced).

---

## 3. Narrator implementation

- **Authority:** presentation-only; no validation, commit, or continuity mutation paths.
- **Context:** derived from committed move + post-commit scene projection + accepted director decision + HG `build_narrator_render_prompt` instructions.
- **Excludes:** `director_scratch`, `character_private`, rejected attempts, uncommitted proposals.
- **Inference:** one ephemeral DSH session per narrator render; plain prose output (not JSON).
- **Behavioral reference:** V1 `build_narrator_render_prompt` + `redact_structured_move_for_orchestration`.

---

## 4. Three-role sequence

```text
1. POST /v1/scenes → POST /v1/rounds/start
2. Scene DSH session; hg/round-started
3. Director: prepare → ephemeral inference → validate → hg/director-accepted
4. Character: prepare → ephemeral inference → validate → commit → hg/move-committed
5. Narrator: prepare_narrator_context (requires domain_commit_id) → ephemeral inference
6. hg/narrator-completed with presentation_text (or hg/narrator-failed)
```

**Ordering invariant:** Narrator events always follow `hg/move-committed`. Commit failure skips narrator entirely.

---

## 5. State-authority proof

| Requirement | Evidence |
|-------------|----------|
| Narrator cannot mutate continuity | No `commit_narration` API; Python `test_narrator_has_no_commit_path` |
| Narrator sees committed state | `committed_move` contribution from round fixture after commit |
| Rejected attempts invisible | `test_narrator_context_reflects_committed_move_not_rejected_attempt` |
| Narrator failure does not roll back canon | Node `narrator failure after commit preserves canon`; `canon_preserved: true` on `hg/narrator-failed` |

---

## 6. Context-isolation proof

| Requirement | Evidence |
|-------------|----------|
| No `director_scratch` | Python + Node isolation tests |
| No `character_private` | Python + Node isolation tests |
| Receives committed move | `committed_move` source_kind in manifest |
| Separate inference session | Integration test: narrator session ≠ director/character/scene |
| Post-commit scene projection | `scene_state` contribution uses post-commit turn counter |

---

## 7. Event/trace model

New log-only events on scene session:

- `hg/narrator-started`
- `hg/narrator-completed`
- `hg/narrator-failed`

Correlation: `hg_scene_id`, `hg_round_id`, `inference_id`, `narrator_inference_session_id`, `domain_commit_id`, `continuity_turn_index`, `manifest_id`, `dsh_scene_session_id`.

Trace reconstructs: round → director → character proposal/retry → domain commit → narrator render.

---

## 8. Failure semantics

When narrator fails after successful commit:

- `presentation_failed: true`, `presentation_rendered: false`
- `hg/narrator-failed` with `canon_preserved: true`, `presentation_failure_class: runtime_render`
- Scene turn counter and `committed_move_count` unchanged from post-commit state
- Future recovery: re-run narrator presentation against same `domain_commit_id` (not implemented this slice)

---

## 9. Runtime efficiency

| Metric | Observation |
|--------|-------------|
| Additional boundary calls | +1 `prepareNarratorContext` per round |
| Narrator manifest size | ~4 contributions (scene, committed_move, director_decision, instruction) |
| DSH session setup | +1 ephemeral narrator inference session |
| Serialization | Same HTTP JSON pattern; no new transport layer |
| Scene correlation | Unchanged — single scene session holds full trace |

---

## 10. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 12 passed |
| `npm test` (v2/rp_runtime) | 11 passed |
| Pre-existing presence-state failure | not re-run in full suite this slice |

---

## 11. Clean-V2 review

| Classification | Items |
|----------------|-------|
| **Permanent** | Domain API narrator contract, `_runNarratorPresentation`, narrator events, three-role `runDirectorCharacterRound` |
| **Promoted** | Shared `_correlation`, `_runEphemeralInference` substrate |
| **Transitional** | HTTP transport, fixture store, mock LLM (unchanged; removal when production transport + real provider) |
| **Test-only** | `narrator-round.test.mjs`, extended isolation/authority tests |
| **Removed** | none |

---

## 12. Challenge/refinement

- Narrator fits naturally as a post-commit presentation phase on the existing Cordis runtime.
- `HolyGrailRpRuntime` remains an orchestrator, not a monolith — role-specific semantics stay in Domain API + small phase methods.
- Shared inference substrate is appropriate; narrator correctly diverges (no JSON validation loop).
- Presentation failure is cleanly separable from canon via event semantics.
- Scene-level DSH correlation remains the right topology for three ephemeral role sessions.
- Second character should fit the same pattern: director selects → per-character ephemeral loop → commit → narrator.
- No new transitional clutter beyond existing HTTP/fixture/mock stack.

---

## 13. Architecture verdict

**Validated with refinements** — three-role basic round proven. Refinements deferred: narrator semantic review (V1 `assess_narrator_render_semantics`), presentation retry/recovery, per-viewer projection.

---

## 14. Repository state

| Field | Value |
|-------|-------|
| Commit | `8dd458c` — feat(v2): add Narrator DSH orchestration after domain commit |
| Branch | `main` |
| `origin/main` | aligned after push |

---

## 15. Next recommended slice

**Second character in cast loop** — extend Director sequencing to hand off between two characters within one round/scene, reusing the same ephemeral inference + commit + narrator pattern. Requires Governance review before implementation.
