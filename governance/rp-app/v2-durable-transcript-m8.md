# V2 Durable Transcript Projection + V1 Deprecation — M8 Implementation Report

**Status:** Completed (M8 — durable RP history projection + V1 deprecation plan)  
**Date:** 2026-08-18  
**M7 user-facing application anchor:** `858a3cf`  
**Implementation HEAD:** (see §21 after commit)

**Governing principle:**

> Holy Grail determines what is true. DeepSeek Harness records what happened.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Initial HEAD | `858a3cf` |
| Assigned / effective workflow weight | standard / **full** |

Pre-slice: 45 Python + 47 Node tests green.

---

## 2. History inventory

| Source | Classification |
|--------|----------------|
| `SessionRepository` + `continuity_state` | **Authoritative domain evidence** |
| `commit_move` / `CharacterTurnRecord` | **Authoritative committed facts** (in-memory per round) |
| `v2_host_state.rp_history` | **Durable presentation projection** (M8) |
| Application `transcript[]` | **UI cache** (rebuilt from domain history on open) |
| DSH inference sessions / `hg/*` events | **Execution evidence** (not transcript authority) |
| V1 `chat_history` in SessionManager JSON | **V1 UI cache** (obsolete for V2) |
| V1 `st.session_state` continuity | **V1 authority** (deprecated) |

---

## 3. Transcript semantics

| Entry kind | Represents |
|------------|------------|
| `user` | Durable user-submitted RP message |
| `committed_turn` | Authoritative structured character action (move beat summary) |
| `presentation` | User-facing Narrator prose linked to `domain_commit_id` |

**Canonical display:** Narrator `presentation` when available; `committed_turn` fallback when presentation failed or missing.

**Domain truth:** committed move in continuity — not Narrator prose.

---

## 4. Durable history architecture

**Option C** — explicit transcript projection stream in `v2_host_state.rp_history`, persisted with session files.

```text
RpHistoryEntry
  entry_id, sequence_index, kind
  hg_round_id?, domain_commit_id?, actor_id?
  content, presentation_status?, metadata, recorded_at
```

- `committed_turn` appended automatically on successful `commit_move` (SessionRepository path)
- `user` recorded via `POST /v1/sessions/history/user-turn`
- `presentation` recorded via `POST /v1/sessions/history/presentation`

---

## 5. User-message durability

User messages persist through Domain Host `record_user_turn` before `runRound()`.

Survive application restart and session reopen.

---

## 6. Presentation persistence

After each round, application client records presentation artifacts per `domain_commit_id`.

Correlation chain:

```text
user message → hg_round_id → domain_commit_id → presentation entry
```

Presentation failure stores `presentation_status: failed` with committed-turn fallback content.

Future `rerender(domain_commit_id)` seam documented — not implemented in M8.

---

## 7. History projection API

| Layer | Contract |
|-------|----------|
| Domain Host | `GET /v1/sessions/{id}/history` → `{ entries, transcript }` |
| Domain Host | `POST /v1/sessions/history/user-turn` |
| Domain Host | `POST /v1/sessions/history/presentation` |
| Application | `GET /api/sessions/{id}/transcript` |
| Application client | `_refreshTranscript()` from domain history |

UI does not parse continuity internals or DSH logs.

---

## 8. Session-open integration

```text
sessions/open → getSessionHistory → project to transcript cache → Streamlit render
```

New turns append via durable history APIs; cache refreshed after each turn.

---

## 9. Presentation failure behavior

- Domain commit remains in continuity and `committed_turn` history
- Failed presentation records `presentation_status: failed`
- Transcript projection shows committed-turn summary with `presentation_failed: true`
- Canon preserved; re-render possible later

---

## 10–11. Validation proofs

- **Restart/resume:** `transcript-projection.test.mjs`, `application-client.test.mjs`
- **Multiple rounds:** turn A + turn B ordering without duplication
- **Python:** `test_session_history.py` (user + commit + presentation survive restart; failure fallback)

---

## 12. DSH trace relationship

DSH logs remain execution diagnostics only. Transcript rebuild requires Domain Host session file only.

---

## 13. Streamlit integration

On session open, fetches `/api/sessions/{id}/transcript` and renders durable history.

---

## 14. V1 vs V2 surface coverage

| Capability | V2 | V1 |
|------------|----|----|
| Supervised launch | ✅ | ❌ manual |
| Durable sessions | ✅ | ✅ (different model) |
| Transcript resume | ✅ M8 | ✅ V1 chat_history |
| User turn | ✅ | ✅ |
| Cast selection | ✅ minimal | ✅ rich |
| Forced speaker | ✅ | ✅ |
| Provider execution | ✅ | ✅ |
| Scene templates / opening modes | ❌ | ✅ |
| Character file picker | ❌ | ✅ |
| Audit UI | ❌ | ✅ |
| Memory/cross-session | ❌ | ✅ |
| Knowledge DB | ❌ | partial V1 |

---

## 15. V1 deprecation decision

**V1 Streamlit entrypoint (`autogen_rp/python/rp_app/app.py`) is marked DEPRECATED.**

Deprecation is justified for core RP loop (launch, session, turn, transcript resume).

**V1 deletion is NOT authorized** — significant UX and memory features remain.

---

## 16. V1 retirement map

| V1 component | V2 replacement | Status | Removal condition |
|--------------|----------------|--------|-------------------|
| `app.py` entrypoint | `npm run app` / `Launch-Holy-Grail-V2.bat` | **Deprecated** | V2 UX parity + governance sign-off |
| `turn_runner` | `HgRoundOrchestrator` | Superseded for V2 | No production workflow depends on V1 runner |
| UI `model_client` bootstrap | DSH `InferenceProfile` | Superseded | V1 entrypoint removed |
| `st.session_state` authority | Domain Host + application client | Superseded | V1 entrypoint removed |
| V1 `chat_history` persistence | `rp_history` projection | Superseded for V2 | V1 sessions migrated or abandoned |
| AutoGen selectors | `ParticipationDecision` | Superseded | V1 entrypoint removed |
| V1 SessionManager as UI authority | `SessionRepository` | Superseded for V2 | V1 deletion slice |

---

## 17. Behavioral validation

| Suite | Result |
|-------|--------|
| Python pytest | **47 passed** |
| Node npm test | **49 passed** |
| Live DeepSeek user turn | **passed** |

---

## 18. Clean-V2 review

**Permanent:** `rp_history`, history APIs, projection functions, session-open transcript rebuild.

**Superseded:** application-memory-only transcript as sole history.

**Transitional:** application transcript cache (rebuilt from domain).

**Deprecated:** V1 Streamlit production entrypoint.

**Test-only:** mock history fixtures, `FixtureStore` (no `rp_history` persist).

---

## 19. Challenge / refinement

One coherent durable history model achieved without duplicate UI database.

User messages and presentations survive restart. Narrator prose remains presentation.

No unnecessary DSH log dependency. V1 deprecation justified but deletion premature due to templates, memory, audit UX gaps.

---

## 20. Architecture verdict

**Validated with refinements**

---

## 21. Repository state

(Updated after commit/push)

---

## 22. Next recommended migration slice

**M9 — V2 cast/character configuration UX:** Port essential V1 character selection and scene setup (templates, character files) into the V2 application API without importing V1 runtime authority. **Do not implement without Governance review.**
