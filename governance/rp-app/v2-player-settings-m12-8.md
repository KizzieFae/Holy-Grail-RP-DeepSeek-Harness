# V2 Player Identity + Production Settings UX — M12.8

**Status:** Complete  
**Date:** 2026-08-18  
**M12.7 anchor:** `55df462`  
**M12.8 completion HEAD:** _(set at commit)_

**Objective:** Complete V2 user-facing configuration for player identity and production inference settings without making Streamlit an authoritative runtime/domain store.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| Pre-slice HEAD | `55df462` |
| `origin/main` | aligned at activation |
| Working tree | clean at activation |
| Workflow | standard / effective **full** |
| Bootstrap profile | full V2 implementation |

### Validation

| Suite | Pre-slice | Post-slice |
|-------|-----------|------------|
| V2 Python | 129 passed, 1 xfailed | **133 passed, 1 xfailed** |
| V2 Node | 55 passed | **63 passed** |
| Neutral domain | 358 passed | **358 passed** |

---

## 2. Reconstructed V1 settings inventory

| V1 setting/control | V2 disposition |
|--------------------|----------------|
| Player character selection | **Retained** — `player_character_file_id` + `control_modes` |
| User display/persona name | **Retained** — `user_persona_id` (distinct from character card) |
| Character card multiselect | **Already migrated** (M9/M12.1) |
| Scene/template selection | **Already migrated** (M9/M12.6) |
| Opening modes | **Already migrated** (M12.6) |
| Role assignments | **Already migrated** (M9) |
| Provider/model (DeepSeek) | **Retained** — application runtime settings |
| Model variants | **Retained** — via `InferenceProfile.model` / advanced routing |
| Reasoning/thinking (`off/low/high/max`) | **Retained** — runtime settings |
| Temperature / max tokens | **Advanced/internal** — sane defaults; not primary Streamlit UX |
| Director/Character/Narrator model choices | **Retained** — simple default + advanced API routing |
| Iteration/retry controls | **Rejected** from normal UX — internal `liveMaxAttempts` default |
| Memory/retrieval toggles | **Rejected** — KnowledgeService owns retrieval; no UI toggle |
| Scene/runtime debug controls | **Optional/debug** — deferred |
| Audit/debug settings | **Deferred optional** |
| API keys | **Environment only** — `DEEPSEEK_API_KEY` |
| Memory scope ID | **Retained** — session semantic; friendlier Streamlit label |
| Prototype cast fallback | **Retained** — dev-only path when catalog unavailable |

---

## 3. Setting authority model

| Class | Examples | Owner |
|-------|----------|-------|
| **A. Durable session/domain** | cast, template, roles, opening, `player_character_file_id`, `user_persona_id`, `memory_scope_id`, `control_modes` | Domain Host `setup_snapshot` |
| **B. Application/user profile** | `user_persona_id` display preference; M11.2 `user_profile` lane for memory | Domain + KnowledgeService contracts |
| **C. Inference/runtime** | model, reasoning, per-role profiles, `liveMaxAttempts` | Application client (`runtimeSettings`) → DSH |
| **D. Presentation/UI-only** | Streamlit layout state, expander open/closed | Streamlit `session_state` |
| **E. Debug/advanced** | per-role API overrides without Streamlit panel, temperature fine-tuning | API/advanced only |

---

## 4. Player identity model

- **Default:** external user speaks via `user_persona_id` (default `"Player"`); all cast members are AI-controlled.
- **Optional:** user selects one `player_character_file_id` from cast; that display name receives `control_mode: player`.
- **User persona ≠ character:** `user_persona_id` is the transcript/memory speaker lane; `player_character_file_id` is an authored card identity.
- **Presence:** player character remains in `present_characters` (Issue #129 posture).
- **No multi-user account system.**

---

## 5. Player-character / control semantics

- `control_modes` map display name → `player` | `ai` stored in `setup_snapshot`.
- Director eligibility excludes `player_controlled` actors (`exclusion_reason: player_controlled`).
- User turns ingress via existing `record_user_turn` with `speaker=user_persona_id`.
- Forced designation can target AI actors; player-controlled actors are not autonomously selected by Director.
- No second turn runner introduced.

---

## 6. Session setup / persistence changes

**`SessionCreateRequest` extended:**
- `player_character_file_id?: str`
- `user_persona_id?: str`

**`setup_provenance_for_ui` extended:**
- `player_character_file_id`, `player_character_display_name`, `user_persona_id`, `control_modes`

**Persistence:** stored in `setup_snapshot` (V2 host metadata); legacy `player_character` field receives display name on save.

---

## 7. Provider/model settings model

- Application `runtimeSettings` object (not Streamlit → DSH direct import).
- Defaults: live DeepSeek `deepseek-v4-flash`, reasoning `low`, shared Director/Character profile, Narrator `reasoningEffort: off`, `maxTokens: 384`.
- Mock mode for tests via client `inferenceMode: 'mock'`.
- Opening generation uses `opening` profile (defaults to narrator-like off/low-token profile).

---

## 8. Per-role routing UX

| Mode | Behavior |
|------|----------|
| **Simple (default)** | One shared profile for Director + Character; Narrator off/low tokens |
| **Advanced (API)** | Distinct `roleProfiles.director/character/narrator/opening` via `PUT /api/settings/runtime` |

Streamlit exposes simple reasoning selector + advanced routing flag (advanced overrides via API, not three selectors in UI).

---

## 9. Reasoning / temperature / token settings

| Setting | Product UX |
|---------|------------|
| Reasoning `off/low/high/max` | **Exposed** — Streamlit selectbox |
| Temperature | **Internal default** — not exposed in normal UX |
| maxTokens | **Internal defaults** (768 character/director, 384 narrator) |
| liveMaxAttempts | **Internal safety** (5) |

---

## 10. Memory / retrieval / scope UX

- **Retrieval:** no user-visible index toggles (M12.7).
- **Memory scope:** optional continuity scope ID field labeled “Continuity scope ID”; blank creates isolated scope.
- No scope management UI beyond reuse-by-ID.

---

## 11. Application settings architecture

```
Streamlit
  → HolyGrailApplicationClient
      → application-settings.mjs (validate + resolve)
      → Domain Host (session semantic)
      → DSH orchestrator (runtime profiles)
```

**API:**
- `GET /api/settings/defaults`
- `GET /api/settings/runtime`
- `PUT /api/settings/runtime`

---

## 12. Validation / error handling

- `validateSessionSetup`: player file in cast, persona non-empty, memory scope format.
- `validateRuntimeSettings`: reasoning enum, roleRouting enum, maxTokens bounds.
- Session create validates before Domain Host call; runtime update returns 400 on invalid settings.

---

## 13. Streamlit production UX

**Session setup:** characters, player identity (display name + play-as), template/roles/opening, continuity scope.

**Model settings:** reasoning level, advanced routing note, apply button.

**RP surface:** transcript + chat input (unchanged layout).

No V1 sidebar wholesale recreation.

---

## 14. Default behavior

New user can create session with default cast selection, default persona `"Player"`, external-user mode, default reasoning `low`, and begin RP without advanced configuration.

---

## 15. Dynamic settings behavior

| Setting | When changeable |
|---------|-----------------|
| Session identity (player, cast, template) | Session create only |
| Runtime inference (reasoning, routing) | Between turns via API/Streamlit apply |
| Runtime settings on reopen | **Not** domain truth — per application launch defaults unless updated |

---

## 16. Traceability / security

- DSH trace continues to record provider/model/reasoning per inference.
- Runtime settings are not written into domain canon / `setup_snapshot`.
- Secrets remain environment-only; UI does not persist API keys.

---

## 17. Player-character integration proof

- **Python:** `test_player_character_excluded_from_eligibility`, control mode persistence, reopen.
- **Node:** eligibility API excludes player; application client round with forced AI designation succeeds.

---

## 18. Role-profile routing proof

- **Node:** `application-settings.test.mjs` — simple shared profiles, advanced distinct models, mock mode resolution.

---

## 19. Restart / reopen proof

- **Python:** `test_player_identity_persists_on_reopen`
- **Node:** app server reopen restores `user_persona_id` + `player_character_file_id`; runtime settings reset to launch defaults (not domain truth).

---

## 20. V1 settings parity matrix

See §2. All significant production settings explicitly classified. No remaining vague “rich settings UX” blocker.

---

## 21. Product-completion impact

**Is player/settings UX still a required blocker?** **No.**

---

## 22. Functional-completion assessment

Holy Grail V2 is **functionally complete as the production replacement** for V1 RP product behavior.

Repository retirement/hygiene (autogen_rp rehome, .NET vendor tree, naming cleanup) remains separate.

---

## 23. Remaining optional enhancements

- Narrator semantic retry
- Audit/debug UI
- Streamlit advanced per-role model pickers (API already supports)

---

## 24. Remaining repository-retirement cleanup

- `autogen_rp` data/test rehome
- .NET vendor tree deletion
- SessionManager/path naming cleanup

---

## 25. Clean-V2 review

| Category | Items |
|----------|-------|
| **Permanent** | `player_identity.py`, session contract fields, eligibility exclusion, `application-settings.mjs`, settings API, Streamlit production controls |
| **Reused** | `InferenceProfile`, `user_profile`, session setup, MemoryService scope, application client/server |
| **Rejected/advanced** | retrieval toggles, retry ceilings, temperature panel, credential UI |
| **Deferred** | narrator retry, audit UI |

---

## 26. Challenge / refinement

| Question | Verdict |
|----------|---------|
| Durable vs runtime settings separated? | Yes |
| Player identity clear? | Yes — persona vs character file |
| Director controls player character? | No — excluded from eligibility |
| Secrets out of persistence? | Yes |
| Streamlit merely consumer? | Yes |
| New user can start with defaults? | Yes |
| Per-role models without orchestration change? | Yes — profile resolution only |
| Reopen restores session identity? | Yes |
| V1 sidebar recreated? | No |

---

## 27. Architecture verdict

**Validated with refinements** — player/settings semantics implemented; advanced per-role Streamlit controls intentionally deferred to API.

---

## 28. Next recommended slice

**Governance review for repository retirement/hygiene** (`autogen_rp` rehome) — not a product blocker.

Do not proceed without Governance review.
