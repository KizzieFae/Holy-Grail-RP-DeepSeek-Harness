# V2 Real Full-Round Validation — Implementation Report

**Status:** Completed (complete real-provider round slice)  
**Date:** 2026-08-18  
**Architecture anchor:** `2ee410321f19e57c4579821ce590f701ccf2eedf`  
**ParticipationDecision anchor:** `baf507e`  
**Real-provider anchor:** `1503060`  
**Implementation HEAD:** `47b0d63`

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `1503060` |
| Pre-slice validation | 37 Python + 25 Node tests green |

---

## 2. Role-profile integration

**Permanent:** `resolveRoleProfiles()` in `inference-profile.mjs`

```text
runRound({ roleProfiles: { director, character, narrator } })
        ↓
_runDirectorPhase({ modelProfile })
_runCharacterTurn({ modelProfile })
_runNarratorPresentation({ modelProfile })
        ↓
_runEphemeralInference (unchanged substrate)
```

- Shared profile via `roleProfiles.default` or `modelProfile` still supported
- `liveMaxAttempts` (default 3) replaces mock-array length when mocks absent
- `livePrompts` override per-role user prompts; defaults in `live-inference-prompts.mjs`
- `role_inference_traces` and `round_timing_ms` returned from `runRound`

No separate live orchestration path.

---

## 3. Live full-round proof

**Fixture:** one-character cast (`Alice`), semantic completion via actor exhaustion.

**Flow validated:**

```text
round start → eligibility → participation → Director (real)
→ validate → Character (real) → validate → commit → Narrator (real) → round complete
```

**Test:** `v2/rp_runtime/tests/real-full-round.test.mjs` (requires `DEEPSEEK_API_KEY`).

---

## 4. Director live behavior

- Receives director manifest only (scene, director-scratch, instruction)
- Returns valid JSON `next_actor` / `end_round` structure
- Python validation authoritative; retries on parse/validation failure
- `inference_trace` on `hg/director-proposed` with provider/model/usage/reasoning

---

## 5. Character live behavior

- Receives character manifest (scene, character, character-private, instruction)
- Structured move must use `beats[].action` (not `description`/`intent`) — enforced by Python
- Live prompt includes explicit schema example
- Retries up to `liveMaxAttempts` on validation rejection
- Commit only via authoritative Python path

---

## 6. Narrator live behavior

- Context from committed move + director decision
- Plain prose output (not JSON)
- Presentation-only; `hg/narrator-failed` preserves canon if provider fails
- `inference_trace` on `hg/narrator-completed`

---

## 7. Full traceability

Reconstructable from `scene_events` + `role_inference_traces`:

| Phase | Evidence |
|-------|----------|
| Scene/round | `hg_scene_id`, `hg_round_id`, `dsh_scene_session_id` |
| Participation | `hg/participation-decision`, `hg/eligibility-snapshot` |
| Director | `hg/director-proposed/accepted`, inference session, trace |
| Character | `hg/move-proposed/committed`, `domain_commit_id`, trace |
| Narrator | `hg/narrator-started/completed`, trace |
| Round | `hg/round-completed`, `completion_reason` |

Three distinct DSH inference sessions per round.

---

## 8. Reasoning/usage evidence

Observed per role (live round, `deepseek-v4-flash`):

| Role | reasoning_effort | reasoning chunks | usage exposed |
|------|------------------|------------------|---------------|
| Director | low | yes | input/output/cache/reasoning tokens |
| Character | low | yes | yes |
| Narrator | off | sometimes (adapter still streams) | yes |

---

## 9. Failure semantics

| Phase | Behavior |
|-------|----------|
| Director failure | No character inference/commit (`director_failure`) |
| Character failure | No commit (`character_failure`) |
| Narrator failure | Commit preserved (`canon_preserved: true`) |
| Provider failure | `hg/inference-failed`, no domain mutation |

---

## 10. Efficiency observations (typical live one-char round)

| Metric | Observed |
|--------|----------|
| DSH inference sessions | 3 (director + character + narrator) |
| Round latency | ~9–18s total |
| Director latency | ~2–4s |
| Character latency | ~3–8s (may include retries) |
| Narrator latency | ~2–4s |
| Character retries | 0–2 when model uses wrong beat schema |

Manifest/context duplication not optimized in this slice.

---

## 11. Future model-routing readiness

**Sufficient.** `roleProfiles` per role already wired through `runRound` without orchestration changes. Future routing is policy configuration only.

---

## 12. Validation

| Suite | Result |
|-------|--------|
| `pytest v2/tests` | 37 passed |
| Node deterministic | 24 passed |
| `provider-failure.test.mjs` | 1 passed |
| `real-inference.test.mjs` | 1 passed (live) |
| `real-full-round.test.mjs` | 1 passed (live) |
| **Total Node** | **26 passed** |

---

## 13. Architecture verdict

**Validated as designed** — complete three-role round runs on real DSH DeepSeek through the same `runRound()` architecture as mock tests.

---

## 14. Deferred

- Per-role model routing policy
- Multi-character live round
- Prompt/schema hardening for fewer character retries
- `dsh-llm-retry` plugin mounting
