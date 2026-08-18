# V2 Cross-Scope Memory Projection Policy — M10.3 Investigation Report

**Status:** Investigation complete — **no implementation authorized**  
**Date:** 2026-08-18  
**M10 investigation anchor:** `1a41571`  
**M10.1 anchor:** `418afa9`  
**M10.2 anchor:** `ee0cff8`  
**Investigation HEAD:** (see §18 after commit)

**Governing principles:**

> Memory informs inference; only continuity commit establishes canon.

> Cross-session memory is explicit and scope-bound, never inferred merely from cast overlap.

> Python Domain Host owns memory semantics and persistence.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD at investigation start | `ee0cff8` |
| `origin/main` | Aligned (`ee0cff8`) |
| Working tree | Clean |
| Assigned / effective workflow weight | standard / **full** |
| Bootstrap profile | full V2 architecture investigation |
| Authorization | **Investigation/design only** — no runtime changes |

**Artifacts reviewed:**

| Area | Primary sources |
|------|-----------------|
| M10.2 MemoryService | `v2/domain_api/memory_service.py`, `cross_scope_memory_repository.py` |
| M10.1 session-local | `memory_write_policy.py`, `memory_retrieval.py` |
| V1 aggregation | `session_manager.py:get_cross_session_memories`, `app_memory_cross_session.py` |
| V1 buckets | `app_memory_summary.py:build_memory_buckets`, `session_lifecycle_save.py` |
| V1 promotion | `cross_session_memory_policy.py` |
| V1 prompt injection | `app_turn_prompting.py`, `prompt_builders.py` |
| V1 docs/tests | `autogen_rp/docs/cross_session_memory.md`, `test_rp_app_rules.py`, `test_cross_session_stabilization.py` |

**Validation (pre-investigation):**

| Suite | Result |
|-------|--------|
| V2 Python (`v2/tests/`) | 67 passed |
| V2 Node (`v2/rp_runtime/tests/`) | 51 passed |

---

## 2. V1 cross-session projection inventory

V1 cross-session behavior is a **load-time aggregation + apply** pipeline, not a durable cross-session store.

```text
session save → memory_buckets + user_relationships → _session_index.json
    ↓
new scene / session load (cast alias intersection filter)
    ↓
get_cross_session_memories() → should_promote_cross_session filter
    ↓
apply_cross_session_memories() → merge into CharacterState.relationships
    ↓
prompt assembly → CROSS-SESSION USER MEMORY / WORLD FACTS / USER PREFERENCES
```

### What V1 promotes

| Material | Source | Scope in V1 | Subject | Copied vs derived | Cap | Prompt use |
|----------|--------|-------------|---------|-------------------|-----|------------|
| **User relationship history lines** | `user_relationships` in index (from saved `CharacterState.relationships[user].history`) | Cast alias intersection | Per character | **Copied** from prior session index | 8 per character | `CROSS-SESSION USER MEMORY` + merged into `PRIVATE STATE` history |
| **Relationship snapshot** | First matching prior session relationship dict per character | Cast intersection | Per character | **Copied** (trust, counts, entity_type) | 1 snapshot | `PRIVATE STATE` trust merge |
| **Relationship trend** | Derived from trust samples + `last_summary` lines across sessions | Cast intersection | Per character | **Recomputed** at aggregation | N/A | Merged into relationship dict (`trust_history`, `relationship_trend`) |
| **Persistent world facts** | `memory_buckets.persistent_world_facts` at save | Cast intersection | **Session-global** (all characters get same list) | **Copied** from index | 8 | `PERSISTENT WORLD FACTS` in every character prompt |
| **User preferences** | `memory_buckets.user_preferences` at save | Cast intersection | **Session-global** | **Copied** | 8 | `USER PREFERENCES / IDENTITY NOTES` in every character prompt |
| **Session summaries** | `memory_buckets.session_summary` at save | Cast intersection | **Session-global** | **Copied** | 8 | **Not wired to character prompts** (aggregated only; report dest `session_summaries_aggregate`) |

### What V1 does **not** promote cross-session

| Material | V1 behavior |
|----------|-------------|
| `character_memory_summary` | Session file only; restored on **resume** of same session |
| `recent_observations` | Same |
| `private_memories` | Same |
| Full transcripts / chat history | Not aggregated |
| Narrator prose | Not aggregated |
| Continuity summary blocks | In-session continuity path only |

### How buckets are built at save (`build_memory_buckets`)

| Bucket | Build logic | Authority / assumptions |
|--------|-------------|----------------------|
| `session_summary` | Last chat line truncated (~80 chars), or `"RP session"` | **Weak** — not LLM summary; last message snippet |
| `persistent_world_facts` | Continuity canon anchors `category=world_fact` (limit 8) + `"Recent recurring location: {location}."` | **Canon-derived** at save time |
| `user_preferences` | Regex on user chat (`i like`, `call me`, etc.) + fallback `"User goes by {name}."` | **Heuristic**; no per-character learner |

### Privacy / perception assumptions in V1

| Issue | V1 behavior |
|-------|-------------|
| Perception filter on cross-session load | **None** — reads saved relationship history regardless of original perception path |
| Cast overlap scope | Any prior session sharing a character alias contributes buckets |
| World facts / preferences | **Broadcast** to all current cast members |
| Promotion filter | `should_promote_cross_session` — interaction markers for relationship **history lines only**; world facts, preferences, session summaries **always promoted** |

### Classification summary

| Item | Classification |
|------|----------------|
| User relationship history | Valuable semantic behavior; unsafe scope model (cast overlap) |
| Relationship snapshot/trust merge | **State**, not memory — duplicates domain relationship values as text merge |
| Session summaries | Obsolete / incomplete wiring — aggregated but not prompt-injected |
| World facts | Valuable continuity information; **wrong plane** (global broadcast, canon-like) |
| User preferences | Mixed — some global identity, some interaction; **wrong scoping** |
| Cast intersection gate | Unsafe/over-broad scope inference |
| `st.session_state.cross_session_memories` | UI cache convenience |
| `memory_buckets` index denormalization | Save-time projection for aggregation |

---

## 3. Candidate category analysis

### A. User relationship history — **implemented (M10.2)**

| Aspect | Assessment |
|--------|------------|
| Value | High — core cross-session continuity |
| V2 status | `cross_scope_user_relationship` lane |
| Gaps vs V1 | V2 does **not** yet merge relationship **state** (trust/trend) on session open — only history lines at retrieval |
| Recommendation | **Keep M10.2 lane**; do not add relationship-state text projection |

### B. Character-specific remembered events (episodic)

| Aspect | Assessment |
|--------|------------|
| V1 | Session-local only (`character_memory_summary` / observer lines) |
| Value | Medium — promises, threats, revelations can matter across sessions |
| Risk | High — full episodic cross-projection ≈ transcript dump; omniscience if perception not preserved |
| Subject specificity | Must be per `subject_character_file_id` |
| Recommendation | **Defer or add only as ultra-narrow tagged subset** (see §15) |

### C. Session summaries

| Aspect | Assessment |
|--------|------------|
| V1 | Weak last-message snippet; aggregated but **not prompt-injected** |
| Value | Low — lossy, non-subject-specific, overlaps `rp_history` / continuity summaries |
| Risk | High omniscience — whole-session compression without subject filter |
| Recommendation | **Reject** for MemoryService cross-scope |

### D. World facts

| Aspect | Assessment |
|--------|------------|
| V1 | Canon anchors + location string; broadcast to all characters |
| Value | Medium for world continuity |
| Authority test | **Canon/knowledge**, not character belief |
| Recommendation | **KnowledgeService** (scope-bound), not MemoryService |

### E. User preferences

| Aspect | Assessment |
|--------|------------|
| V1 | Regex on user messages; global within cast overlap |
| Value | Medium for UX (names, style) |
| Character specificity | Often **user-global**, not character-learned |
| Recommendation | **UserProfile / KnowledgeService** with explicit scope; MemoryService only when a specific character perceived the preference statement |

### F. Relationship-state explanations

| Aspect | Assessment |
|--------|------------|
| V1 | Merges trust + `last_summary` + trend on apply |
| Distinction | State (`trust`) ≠ evidence (`history` lines) |
| M10.2 | Projects **history evidence** only |
| Recommendation | **Do not** project current trust/trend as cross-scope text; if needed at session open, hydrate relationship **state** from domain model — not memory records |

### G. Scene/location history

| Aspect | Assessment |
|--------|------------|
| V1 | `"Recent recurring location: …"` folded into world facts |
| Value | Low as character memory |
| Recommendation | **Scope metadata or KnowledgeService** location context — not per-character memory |

### H. Other V1 buckets

No additional named buckets beyond the three `memory_buckets` keys. Relationship `last_summary` is folded into trend computation, not a separate cross-scope lane.

---

## 4. Memory vs knowledge classification

| Information | Canon? | Character belief? | V2 destination | Cross-scope via MemoryService? |
|-------------|--------|-------------------|----------------|--------------------------------|
| Committed scene events | Yes (continuity) | Partial (interpretations) | Continuity + session-local episodic | No (session-local episodic only) |
| Canon anchors `world_fact` | Yes | N/A | **KnowledgeService** / continuity projection | **No** |
| Location at session end | Borderline canon | N/A | KnowledgeService or scope metadata | **No** |
| User said "call me X" | No | Perceiver belief | Relationship history (if perceived) or UserProfile | **Only via M10.2 relationship line if character perceived** |
| User global style preference | No | Unclear learner | **UserProfile / KnowledgeService** | **No** (unless character-specific evidence) |
| Relationship trust value | Domain state | N/A | CharacterState.relationships | **No** (state hydration, not memory text) |
| Relationship history line | No | Yes | MemoryService `cross_scope_user_relationship` | **Yes (M10.2)** |
| Session summary snippet | No | No | **Reject** / rp_history evidence | **No** |
| High-salience promise/threat | No | Yes (subject) | Potential future `cross_scope_episodic` | **Deferred** |
| Card lore | Authored | N/A | KnowledgeService / character profile | **No** |

**Rule (recommended):**

```text
If true for all informed characters in the scope → KnowledgeService / continuity canon
If true only as this character's experienced/perceived belief → MemoryService (subject-bound)
If merely what happened in chat → rp_history evidence; not automatic memory
```

---

## 5. Projection eligibility criteria

A record may become cross-scope **memory** only if **all** apply:

1. **Durable source** — written after authoritative session-local memory policy (user turn persist or commit hook).
2. **Explicit scope** — `memory_scope_id` matches; never inferred from cast.
3. **Explicit subject** — `subject_character_file_id` required.
4. **Perception grounding** — subject was present and passed perception filter at source write (or was acting character for actor episodic).
5. **Character belief** — content represents what the subject remembers, not objective world truth.
6. **Cross-session utility** — useful in a **different** session with same scope + subject.
7. **Not duplicate transcript** — bounded line, not raw chat/transcript chunk.
8. **Not canon dump** — world facts and global preferences excluded unless reclassified to KnowledgeService.
9. **Provenance retained** — `source_session_id`, content fingerprint, perception basis.
10. **Bounded** — fits per-category cap and total token budget.

---

## 6. Perception/provenance requirements

Cross-scope records must be able to answer: *Why does this character remember this?*

| Field (current or future) | Purpose |
|---------------------------|---------|
| `source_session_id` | Which session created the memory |
| `source_domain_commit_id` / `source_hg_round_id` | Event anchor when available |
| `user_persona_id` | For relationship lines |
| `provenance.perception_filtered` | M10.2 user-turn flag |
| `provenance.projection` | Lane identifier |
| **Recommended if episodic added:** `perception_basis` | `actor` \| `observer` \| `user_addressed` |
| **Recommended if episodic added:** `source_event_kind` | `user_turn` \| `character_commit` |

**Invariant (unchanged):**

> Cross-session memory cannot reveal information the character could not perceive in the source session.

V1 violates this on load (replays saved history without re-checking perception). V2 must not regress.

---

## 7. Salience/selectivity policy

**Do not** project every session-local episodic line.

Deterministic salience signals (no LLM):

| Signal | Eligible for future episodic projection? |
|--------|------------------------------------------|
| User relationship line (perceived) | **Yes** — M10.2 |
| User preference regex match | **No** — KnowledgeService unless character-specific |
| Actor self-trace (`recent_observations`) | **No** — session-local only |
| Observer "Observed: …" line | **Maybe** — only with high-salience tag |
| Interpretation with goal/tactic only | **No** — too mundane |
| Lines containing promise/threat/revelation markers | **Maybe** — deterministic keyword/tag policy |
| Canon anchor statements | **No** — knowledge |
| Session save summary snippet | **No** |

**Recommended salience tags (future episodic lane only):**

`promise`, `threat`, `revelation`, `relationship_shift` — assigned by deterministic rules at **write** time, not retroactive LLM scoring.

---

## 8. Record-contract implications

**M10.2 contract is sufficient for relationship lane.**

Add fields **only if** a future episodic lane is authorized:

| Field | Needed for |
|-------|------------|
| `perception_basis` | Episodic eligibility audit |
| `source_event_kind` | Distinguish user vs character commit sources |
| `salience` | Deterministic filter/ordering |
| `related_entities` | Optional; defer until proven necessary |

Do **not** add `world_fact_reference` to memory records — world facts belong in KnowledgeService with their own IDs.

---

## 9. Retrieval lanes and token budgeting

### Keep lanes separate (recommended)

| Lane | Status | Cap (recommended) |
|------|--------|-------------------|
| `session_local_episodic` | M10.1 | 5 + 5 lines (existing) |
| `cross_scope_relationship` | M10.2 | 8 records (existing) |
| `cross_scope_episodic` | **Not implemented** | 4–6 records if authorized |
| `cross_scope_user_preference` | **Not recommended** | N/A — use KnowledgeService |

### Total cross-scope budget (recommended)

- Per subject per `prepare_context`: **≤ 12 records** across cross-scope lanes
- Per contribution: **≤ ~1.5k chars** projected text
- Deterministic ordering: `created_at` ascending, then `memory_id`
- Within-lane: recency tail after salience filter

### Why separate lanes

- Provenance clarity for debugging and V1 retirement
- Independent caps (relationship vs episodic)
- Future backend replacement without ContextAssembly churn

---

## 10. Projection lifecycle

**Recommended (continue M10.2 model):**

```text
authoritative user turn (or future: commit_move for episodic)
    ↓
session-local MemoryWritePolicy
    ↓
SessionRepository.persist  (authoritative)
    ↓
cross-scope eligibility test (deterministic)
    ↓
build projection record(s)
    ↓
CrossScopeMemoryRepository.append (idempotent)
```

| Trigger | M10.2 | Future episodic (if any) |
|---------|-------|---------------------------|
| User turn | **Yes** | N/A |
| Character commit | No | **Only if salience tags match** |
| Session close | No | **No** — avoid batch omniscience |
| Session save buckets | **No** — reject V1 bucket copy pattern |

---

## 11. Failure/idempotency posture

**Continue M10.2 posture:**

```text
session commit succeeds
cross-scope projection failure → log + retryable
no rollback of session-local memory or continuity
```

Broader categories do **not** change this. Cross-scope remains `authority_class=derived` and non-authoritative for canon.

Idempotency: stable `memory_id` fingerprint prevents duplicate projection on retry.

---

## 12. Historical backfill assessment

| Question | Assessment |
|----------|------------|
| Feasibility | Relationship history backfill possible from saved `CharacterState` in prior V2 sessions sharing scope |
| Provenance quality | **Poor** for old events — perception basis not stored historically |
| Risk | Reintroduces V1-style load without perception re-validation |
| Need | Low — opt-in scopes are new; explicit sharing is deliberate |

**Recommendation:** **New events only** for any future lane. If backfill ever needed, require a dedicated migration job with explicit `perception_basis=unknown_legacy` and Governance approval — not silent promotion.

---

## 13. Vector retrieval assessment

| Question | Answer |
|----------|--------|
| Needed for relationship lines? | **No** — subject + scope + recency sufficient |
| Needed for narrow episodic tags? | **No** at expected scale (≤ tens of records per subject) |
| Scale threshold | Consider semantic retrieval only at **hundreds+** records per subject per scope **and** evidence that deterministic caps lose critical recall |
| Provider seam | `CrossScopeMemoryRepository` behind `MemoryService` remains replaceable; vector would be a **retrieval plugin**, not a write-path change |

**Defer vectors.** Deterministic subject/category/recency/salience filters are sufficient for the recommended near-term scope.

---

## 14. V1 retirement impact

| V1 artifact | V2 destination | Migrate / reject | Removal condition |
|-------------|----------------|------------------|-------------------|
| Cast-overlap aggregation | Explicit `memory_scope_id` | **Migrated** (M10.2) | V2-only path |
| `character_user_memories` / history apply | `cross_scope_relationship` retrieval | **Migrated** | V1 load/apply unused |
| Relationship snapshot/trust merge on apply | CharacterState relationship **state** at session open (if needed) | **Reject as memory text** | Domain hydration spec |
| `persistent_world_facts` cross-session | **KnowledgeService** (scope-bound) | **Migrate elsewhere** | Knowledge slice complete |
| `user_preferences` cross-session | **UserProfile / KnowledgeService** | **Migrate elsewhere** | Knowledge slice complete |
| `session_summaries` aggregation | **Reject** | **Reject** | Remove dead aggregation code in V1 retirement |
| `memory_buckets` save denormalization | Per-lane projection at write time | **Replace** | No V1 index bucket dependency |
| `should_promote_cross_session` heuristics | Deterministic write-time eligibility | **Replace** | Cross-scope write policy in MemoryService |
| `st.session_state.cross_session_memories` | Domain Host repository | **Migrated** (M10.2) | Streamlit V2 only |

---

## 15. Recommended M10.3 implementation scope

### Recommendation: **Option 4** (primary) with **Option 1** for MemoryService

**Do not implement broader MemoryService cross-scope projection in M10.3.**

| Action | Scope |
|--------|-------|
| **Stop MemoryService expansion here** | M10.2 user-relationship lane is sufficient for memory cross-scope |
| **Next implementation slice** | **KnowledgeService migration** for scope-bound world facts + user-global preferences |
| **Explicitly reject** | Session summaries, world-fact broadcast, global preference broadcast as character memory |
| **Defer (optional future)** | Ultra-narrow `cross_scope_episodic` for salience-tagged promises/threats/revelations — only if product evidence shows relationship lines are insufficient |

### What M10.3 implementation would **not** include

- No new `memory_kind` lanes
- No session-close batch projection
- No relationship trust/trend text projection
- No V1 `memory_buckets` port
- No vectors
- No backfill

### If Governance later authorizes episodic cross-scope (hypothetical M10.4)

Smallest useful policy:

```text
memory_kind: cross_scope_episodic
eligibility: character commit OR perceived user turn
salience: deterministic tag ∈ {promise, threat, revelation, relationship_shift}
perception_basis: required
cap: 4 per subject
exclude: mundane observer lines, goal/tactic-only interpretations
```

---

## 16. Challenge/refinement

| Challenge | Response |
|-----------|----------|
| Preserving V1 buckets because they exist? | **No** — session summaries barely reach prompts; world facts/preferences are mis-scoped |
| Whole-session summaries omniscient? | **Yes** — reject |
| World facts actually knowledge? | **Yes** — KnowledgeService |
| Broader memory leak private info? | **Yes** if episodic dump or global broadcast — avoid |
| User preference scoped correctly in V1? | **No** — global regex; fix in KnowledgeService |
| Clear subject per record? | M10.2 yes; future episodic must preserve |
| Salience deterministic? | Required; no LLM scoring |
| Token growth bounded? | Yes with per-lane caps |
| Provenance meaningful? | M10.2 yes; V1 apply loses source session on apply stage |
| Vectors necessary? | **Not now** |
| Simplifies V1 retirement? | **Yes** — clear split: memory = subject belief; knowledge = scope truth |
| Stop memory migration → KnowledgeService? | **Yes** — recommended pivot |

---

## 17. Architecture verdict

**Remaining V1 cross-session material belongs in KnowledgeService** — not further MemoryService expansion.

M10.2 established the correct memory boundary. User-relationship history is the only V1 cross-session semantics that cleanly satisfies the authority, perception, and subject-specificity tests. World facts, global preferences, and session summaries fail the memory vs knowledge distinction and/or V2 safety model.

---

## 18. Repository state

| Item | Value |
|------|-------|
| Investigation commit | (this document) |
| Runtime changes | **None** |
| Branch | `main` |

---

## 19. Next recommended implementation slice

**M11 — KnowledgeService foundation + scope-bound world facts and user-global preferences** (Governance review required)

Implement authoritative, scope-bound knowledge retrieval for:

- canon/world facts (from continuity anchors, not character memory broadcast);
- user-global identity/preferences (explicit scope, not cast overlap);
- deterministic ContextAssembly contributor with `authority_class` distinct from `derived` memory.

Do **not** implement without Governance review. Do **not** add MemoryService cross-scope lanes in the same slice.
