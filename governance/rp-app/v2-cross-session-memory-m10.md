# V2 Cross-Session Memory Architecture — M10 Investigation Report

**Status:** Investigation complete — **no implementation authorized**  
**Date:** 2026-08-18  
**M9 authored-setup anchor:** `38f3d05`  
**Investigation HEAD:** (see §22 after commit)

**Governing principle:**

> Python Domain Host owns authoritative memory semantics, write policy, and retrieval. DSH execution history and M8 transcript are evidence — not memory by themselves.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD at investigation start | `38f3d05` |
| `origin/main` | Aligned |
| Working tree | Clean |
| Assigned / effective workflow weight | standard / **full** |
| Bootstrap profile | full V2 architecture investigation |
| Authorization | **Investigation/design only** — no runtime changes |

**Validation (pre-investigation):**

| Suite | Result |
|-------|--------|
| V2 Python (`v2/tests/`) | 51 passed |
| V2 Node (`v2/rp_runtime/tests/`) | 51 passed |

---

## 2. V1 memory inventory

V1 implements **three distinct memory planes** that must not be conflated in V2.

### Plane A — In-session `CharacterState` (authoritative per character, per session)

| Mechanism | Location | Persistence | Prompt use |
|-----------|----------|-------------|------------|
| `private_memories` | `character_state_model.py` | Session JSON `metadata.character_states` | **Not injected** — audit/fuller trail |
| `character_memory_summary` | same | same | **Primary episodic prompt source** (tail 5 lines) |
| `recent_observations` | same | same | Self-trace prompt source (tail 5 lines) |
| `relationships` (incl. `entity_type: "user"`) | same | same | Identity + cross-session user relationship context |
| `remember_event()` | `character_state_model.py` | Via lists above | Writes summary + private trail |
| `remember_user_interaction()` | same | same | User relationship history (cap 8), trust |

**Write triggers** (`memory_layer/writes.py`, `app_memory_recording.py`):

| Event | Policy |
|-------|--------|
| Successful bot character turn | Actor episodic (interpretation ladder #208); observer episodic filtered by `event_knowledge_recipients` + audibility |
| User message | `remember_user_interaction` on **all** present cast members |
| LLM consolidation | **None** — deterministic caps only (20/12/8) |

**Classification:** Real product semantics. Not a cache.

### Plane B — Cross-session aggregation (derived, not a separate store)

| Mechanism | Location | When loaded |
|-----------|----------|-------------|
| `SessionManager.get_cross_session_memories()` | `session_manager.py` | Scene start / session load |
| `load_cross_session_memories` / `apply_cross_session_memories` | `app_memory_cross_session.py` | Streamlit lifecycle |
| `cross_session_memory_policy.py` | env toggle `RP_CROSS_SESSION_MEMORY` (default on) | Promotion filter for string buckets |

**Aggregated from `_session_index.json` + prior session `memory_buckets` and `user_relationships`:**

- Session summaries
- Persistent world facts (from continuity canon anchors + location at save)
- User preferences (regex on chat history)
- Per-character user relationship history lines
- Relationship snapshots / trust trends

**Scope filter (actual V1 behavior):** Prior session included only if `session.characters` aliases **intersect** current cast aliases (`session_manager.py:477`). **No `campaign_id` or world key exists.**

**Not aggregated cross-session:** `character_memory_summary`, `private_memories`, `recent_observations` from other sessions. Those remain inside each session file and restore only when **that session** is reopened.

**Classification:** Real product semantics for user-relationship continuity; implementation is **recomputed projection** not durable cross-session episodic store.

### Plane C — Continuity-derived episodic retrieval (read-only, flag-gated)

| Mechanism | Location | Authority |
|-----------|----------|-----------|
| `episodic_memory_compile.py` | Deterministic templates from `PublicEvent`, interpretations, issues | `non_authoritative=True` |
| `episodic_memory_select.py` | Visibility + dedup; cap 6 items / 2400 chars | Read path |
| `episodic_memory_cache.py` | `st.session_state` SHA-256 cache | **Runtime cache** |
| `retrieved_episodic_merge.py` | Merges into `RetrievedContextBundle` scope `session_episodic` | Prompt gap-fill |

Enabled by `RP_EPISODIC_MEMORY=1`. Does not write memory.

**Classification:** Session-local retrieval lane; distinct from CharacterState episodic lists.

### Plane D — Continuity authority (not "memory" but related)

`ContinuityManager`: public events, canon anchors, issues, summary blocks. Authoritative scene truth. Deterministic summary blocks (`continuity_summary_helpers.py`) — **not LLM-generated**.

### V1 caches / workarounds

| Item | Classification |
|------|----------------|
| `st.session_state.cross_session_memories` | Loaded projection cache |
| `st.session_state.episodic_memory_candidate_cache` | Compile cache (not wired to scene reset in prod) |
| `should_promote_cross_session` | Quality filter on aggregation strings |
| `memory_buckets` at save | Denormalized index-friendly projection |

### V2 current state (gap baseline)

| V1 capability | V2 status (M9) |
|---------------|----------------|
| `CharacterState` in session persistence | ✅ Persisted via `SessionRepository` |
| Memory writes on `commit_move` | ❌ Not wired |
| `memory_layer` retrieval in `prepare_context` | ❌ Prototype scene + card `lore_facts` only |
| Cross-session aggregation on session create | ❌ Not wired |
| Continuity-derived episodic retrieval | ❌ Not wired |
| M8 `rp_history` | ✅ Durable transcript; **not** character memory |

---

## 3. Memory semantic model

| Concept | Definition | V1 mapping |
|---------|------------|------------|
| **Authoritative domain fact** | True in continuity / canon | `ContinuityManager` canon anchors, committed moves |
| **Character memory** | What a character believes/remembers | `CharacterState` episodic lists + relationships |
| **Episodic memory** | Remembered event/interaction | `remember_event`, observer lines, user relationship history |
| **Derived interpretation** | Character conclusion about an event | `character_memory_summary` lines (director reason / motivation) |
| **Relationship memory** | Ongoing stance toward entity | `relationships` dict (user + character entities) |
| **Summary** | Compressed prior events | Continuity `SummaryBlock`; session `memory_buckets.session_summary` |
| **Execution history** | DSH inference evidence | DSH sessions — **not memory** |
| **Transcript / history** | M8 durable user-visible record | `rp_history` — **evidence for memory policy, not memory itself** |

**Distinctions V1 partially enforces:**

- Continuity ≠ CharacterState (separate stores)
- Cross-session aggregation ≠ full episodic replay
- Episodic compile lane explicitly `non_authoritative`
- `private_memories` ≠ prompt-injected summary

**Distinctions V1 does not fully enforce:**

- Character memory vs canon (interpretation can sound factual)
- World scope (shared-cast heuristic only)
- Card-authored lore vs earned episodic memory (both can reach prompts)

---

## 4. Scope and identity model

### What V1 actually does

| Question | V1 answer |
|----------|-----------|
| Same character, two sessions, shared cast? | User relationship history + buckets **aggregate** into new session |
| Same character, unrelated cast/session? | **No aggregation** (cast intersection gate) |
| Reopen same session? | Full `CharacterState` episodic lists restored from session JSON |
| Kizzie in World A vs World B? | **No world boundary** — only cast overlap matters |

### Recommended V2 identity model

**Two-tier model** (preserves V1 value, fixes bleed risk):

```text
memory_scope_id
    + subject_character_file_id   (from M9 setup_snapshot / character_file_ids)
    + optional subject_user_persona_id
```

| Field | Semantics |
|-------|-----------|
| `subject_character_file_id` | Stable authored ID (`kizzie`, `willow`) — survives display renames within snapshot semantics |
| `memory_scope_id` | Explicit continuity boundary — **required architectural addition** |

**Default scope proposals (pick one at implementation; Governance decision):**

1. **`cast_lineage:{hash(sorted character_file_ids)}`** — V1-parity implicit party scope
2. **`continuity_profile:{user-assigned id}`** — explicit campaign/world (recommended long-term)
3. **`session_local`** — in-session only (no cross-session writes)

**M9 interaction:** Session stores `character_file_ids` and card snapshot. Memory must key off **file ID**, not display name alone. Display name remains canonical **actor_id** for in-session turns.

**Unresolved question (focused):** Product choice of default `memory_scope_id` when user does not configure a continuity profile. V1 behavior ≈ option 1; safer default for unrelated stories ≈ option 3 until user opts in.

---

## 5. Memory authority rules

| Rule | Policy |
|------|--------|
| Memory ≠ canon | Memories inform character inference; only `commit_move` + continuity rules establish canon |
| Memory may be wrong | Interpretation lines are `derived` authority class in manifests |
| Memory may be stale | Supersede/link records; do not silent overwrite |
| Cross-character isolation | Subject character_id required on every record; retrieval filtered by subject |
| DSH output | **Never** auto-persisted as memory |
| Transcript | May **trigger** memory policy; not stored wholesale as character memory |
| Authored card lore | `KnowledgeService` / `character_profile` — not episodic memory |

---

## 6. Write policy

**Authoritative sequence:**

```text
committed domain event (move accepted / user turn recorded)
        ↓
perception / audibility / presence evidence
        ↓
deterministic memory write policy (memory_layer semantics)
        ↓
memory candidate(s)
        ↓
MemoryService.persist (session-local and/or cross-scope)
```

### Write sources (V1-proven, V2 should preserve)

| Source | When | Deterministic? |
|--------|------|----------------|
| Character turn commit | After successful `commit_move` | Yes — interpretation ladder + observer recipients |
| User message | After durable user turn record | Yes — truncated summary to all cast |
| Relationship changes | Embedded in `remember_user_interaction` | Yes |
| Continuity canon anchors | At session save → `memory_buckets` | Yes |
| LLM post-session consolidation | **Not in V1** | Defer |

### V2 hook point

`DomainKernel.commit_move` → invoke `MemoryWritePolicy` (extracted from `memory_layer/writes.py`) → `MemoryService` updating session `CharacterState` + optional cross-scope projection.

**Not authorized in M10:** implementing hooks.

---

## 7. Perception/privacy model

V1 enforces at write time (`memory_layer/writes.py`):

- `normalize_move_audibility`
- `event_knowledge_recipients` for observer episodic lines
- Present-character list from `scene_state.present_characters`

**Architectural invariant (V2 must preserve):**

> Memory cannot grant a character information that ContextAssembly would have denied at the time of the event.

**V1 gap:** User message memory writes to **all** cast without per-character perception filter (`commit_user_message_memory`). Accept as known product behavior or tighten in V2 with explicit policy flag.

**Private card material:** Stays in `character_private` contributions (M9); not episodic memory unless earned through perceived events.

---

## 8. Retrieval semantics

| Lane | Mandatory? | Mechanism |
|------|------------|-----------|
| Session-local episodic (interpretation + self-trace) | **Yes** when character has memories | Deterministic tail selection (5+5) |
| Cross-session user relationship / buckets | **Yes** when scope enabled | Deterministic aggregation + promotion filter |
| Continuity-derived episodic compile | Optional (flag) | Deterministic compile + dedup |
| Authored knowledge / lore | Separate `KnowledgeService` | Deterministic index |
| Vector semantic search | **No** — not required for parity | Future plugin |

**Rule:** Correctness-critical identity, scene grounding, and recent in-session episodic tails must not depend on model tool invocation.

### Mandatory vs optional

| Mandatory context memory | Optional deep recall |
|--------------------------|------------------------|
| Identity + goals (character profile) | `recall_memory` tool (future) |
| Recent interpretation tail | Semantic search across long history |
| Active user relationship summary | Full `private_memories` audit trail |
| Cross-scope user history (if enabled) | Operator memory browser |

---

## 9. Knowledge vs memory relationship

```text
KnowledgeService
    = authored / world / reference material (card lore, templates, indexes)

MemoryService
    = character-specific remembered experience (earned through play)
```

| Question | Answer |
|----------|--------|
| Shared retrieval infrastructure? | Yes — `RetrievalProvider` interface behind both services |
| Same authority filters? | **No** — knowledge lacks perception basis; memory requires subject + scope |
| Knowledge → memory? | Only through explicit domain event ("character learned X") |
| Memory → canon? | **No** automatic promotion; director/continuity commit only |
| V1 `authored_retrieval_index` | Knowledge lane — not MemoryService |

---

## 10. M8 history relationship

```text
rp_history = durable session transcript (user, committed_turn, presentation, opening)

memory     = selected character-specific persistence (may cite source evidence)
```

| `rp_history` role | Verdict |
|-------------------|---------|
| Source evidence for memory generation | ✅ Appropriate |
| Sufficient alone for cross-session memory | ❌ Too verbose; lacks perception filtering and subject model |
| Same as memory | ❌ |

Memory write policy may **read** `rp_history` + `domain_commit_id` + continuity rows when reconstructing provenance, but must not dump transcript into character context as "memory."

---

## 11. Storage options

| Option | Assessment |
|--------|------------|
| **A — Extend SessionRepository only** | Sufficient for **session-local** episodic (V1 parity on reopen). **Insufficient** alone for explicit cross-scope memory records. |
| **B — MemoryService + file-backed repository** | **Preferred initial backend** — JSON/file records keyed by `(memory_scope_id, subject_character_file_id)`; aligns with mature plugin doc. |
| **C — Relational DB** | Future — structured queries, provenance indexes |
| **D — Relational + vector** | Future — semantic recall plugin |
| **E — Graph** | Optional for relationship-heavy queries; not first slice |

**Preferred architecture:**

```text
MemoryService (Python, authoritative policy)
    ↓
MemoryStore interface
    ├── SessionCharacterStateAdapter (in-session lists — Plane A)
    ├── CrossScopeMemoryRepository (Plane B durable records or index projections)
    └── (future) VectorMemoryIndex plugin
```

Session JSON remains source for **session-local** state on reopen. Cross-session may continue **index aggregation** initially (V1 parity) while introducing explicit `memory_scope_id` for new writes.

---

## 12. Memory record contract (minimum)

```text
memory_id
memory_scope_id
subject_character_file_id
subject_display_name_at_write   # audit only
memory_kind                     # episodic_interpretation | episodic_observation | user_relationship | world_fact_derived
content
authority_class                 # derived | suggestive (not authoritative canon)
source_session_id
source_domain_commit_id?        # when applicable
source_hg_round_id?
perception_basis?               # recipients, audibility class
related_character_ids[]
importance                      # optional rank
created_at
supersedes_memory_id?           # optional revision chain
```

Every record must answer: **Why does this character remember this?**

---

## 13. ContextAssembly integration

```text
Character inference requested
        ↓
DomainKernel.prepare_context (evolves to ContextAssembly)
        ↓
MemoryService.retrieve(scope, subject_character_file_id, scene_context)
        ↓
authority + perception filter
        ↓
PromptContribution(s) source_kind=character_memory | relationship_memory
        ↓
PromptContributionManifest
        ↓
HgContextBridge → DSH
```

| Contribution | `source_kind` | `authority_class` |
|--------------|---------------|-------------------|
| Episodic tail | `character_memory` | `derived` |
| User relationship | `character_profile` or new `relationship_memory` | `derived` |
| Cross-scope buckets | `character_memory` | `suggestive` |

Provenance must include `memory_id`, `memory_scope_id`, `source_session_id`, `source_domain_commit_id`.

**V2 today:** `prepare_context` injects scene + card private secret only — memory contributor is the primary M10 implementation gap.

---

## 14. Optional tools/skills assessment

| Tool | Value | Priority |
|------|-------|----------|
| `recall_memory` | Deep search across long history | Low — after deterministic baseline |
| `search_personal_history` | User agency for reflection scenes | Low |
| `inspect_relationship_memory` | Debugging / RP inspection | Medium for audit UI slice |

**Do not implement in M10.** Mandatory context must not depend on these.

---

## 15. Cross-session lifecycle

```text
Session A (scope S, character kizzie)
  user turn + character commits
      ↓
MemoryWritePolicy (perception-filtered)
      ↓
Session-local CharacterState update (persisted in session A JSON)
      ↓
On session save/close: project cross-scope records OR index buckets for scope S

--- application closes ---

Session B (same scope S, character kizzie selected)
  sessions/create with character_file_id kizzie, memory_scope_id S
      ↓
MemoryService.load_cross_scope(S, kizzie)
      ↓
Merge into live CharacterState relationships / cross-session prompt buckets
      ↓
prepare_context → memory contributions
      ↓
DSH character inference
```

**Stable link:** `memory_scope_id` + `character_file_id` (not display name alone).

---

## 16. World/campaign isolation

**V1:** Implicit shared-cast clustering only — **risk of bleed** when same character file used in unrelated stories with overlapping cast names.

**V2 requirement:** Introduce explicit `memory_scope_id` at session create (optional field, sensible default documented by Governance).

| Scenario | Isolation |
|----------|-----------|
| Same card, same scope | Memories shared (intended) |
| Same card, different scope | **No recall** |
| Same display name, different card file | Isolated by `character_file_id` |

Until scope is configured, default should bias **conservative** (session-local only) or require opt-in cross-session — **Governance must decide**.

---

## 17. UI-safe boundary

Future UI may expose:

- Character memory list (interpretation lines, relationship summaries)
- Forget / correct with provenance
- Cross-session scope indicator

**API rules (mirror M9):**

| UI-safe | Domain-only |
|---------|-------------|
| `memory_id`, kind, truncated content, timestamp, scope | Full `private_memories` audit trail |
| Relationship trust / trend summary | Raw perception basis internals |
| Source session id | Other characters' private memories |

No memory UI in M10.

---

## 18. V1 retirement map

| V1 responsibility | V2 replacement | Removal condition |
|-------------------|----------------|-------------------|
| `st.session_state.character_states` live authority | `LiveSession.character_states` + Domain Host | V2 write path proven |
| `app_memory_recording.py` Streamlit hooks | `MemoryWritePolicy` on `commit_move` / `record_user_turn` | Kernel hooks green |
| `load_cross_session_memories(st_module)` | `MemoryService.load_cross_scope` at session create | Scope model decided |
| `st.session_state.cross_session_memories` cache | Application holds read-only projection from Domain Host | App never aggregates sessions |
| `memory_layer/retrieval.py` in prompt_builders | `prepare_context` memory contributor | Context isolation tests pass |
| `episodic_memory_cache` in Streamlit | Domain-side compile cache keyed by continuity version | Episodic lane ported or deferred |
| Direct prompt injection in `prompt_builders.py` | `PromptContributionManifest` only | V2 round uses manifest path |
| `memory_buckets` denormalization | MemoryService projection to session index | Index write policy defined |

---

## 19. Recommended implementation sequence

Prove hardest invariant first: **perception-grounded write + session-local retrieve without cross-session complexity**.

| Slice | Scope | Proves |
|-------|-------|--------|
| **M10.1** | Extract `MemoryWritePolicy` from `memory_layer/writes.py`; hook `commit_move` + `record_user_turn` in Domain Kernel; persist in session `CharacterState`; deterministic retrieval contributor in `prepare_context` | Write policy + perception + context isolation |
| **M10.2** | Introduce `MemoryService` interface + `memory_scope_id` on session create; session-local store adapter | Clean boundary; backend independence |
| **M10.3** | Cross-scope aggregation (V1 parity: user relationship + buckets) with explicit scope key | Cross-session lifecycle |
| **M10.4** | Continuity-derived episodic compile lane (flag-gated, non-authoritative) | V1 Plane C parity |
| **M10.5** | Optional vector provider behind `RetrievalProvider` | Semantic recall — only if needed |

**Do not start with vectors or graph.**

---

## 20. Challenge/refinement

| Challenge | Response |
|-----------|----------|
| Transcript mistaken for memory? | Separated — `rp_history` is evidence, not recall |
| Character memory mistaken for canon? | `authority_class: derived` on memory contributions |
| Cross-character leak? | `subject_character_file_id` on all records + retrieval filter |
| Cross-world bleed? | **Unresolved** — requires `memory_scope_id` (§4, §16) |
| Stable identity sufficient? | File ID + scope; display name is actor_id only |
| Write policy grounded in commits? | V1 proves pattern; V2 must hook `commit_move` |
| LLM consolidation needed? | **No** — V1 does not use it |
| Vectors needed now? | **No** — deterministic tails + aggregation suffice |
| MemoryService independent of backend? | Yes — interface + session adapter first |
| Importing V1 caches? | **Reject** — port `memory_layer` policy, not Streamlit caches |
| V1 removable after? | Yes, once kernel owns write/read and app stops aggregating |

---

## 21. Architecture verdict

**Mature memory architecture established with one focused unresolved question.**

The three-plane V1 model maps cleanly to V2 Domain Host ownership. The design is sound if implementation:

1. hooks writes to **committed events** only;
2. keeps transcript and memory separate;
3. introduces explicit **`memory_scope_id`** before broad cross-session recall.

**Focused unresolved question:** Default `memory_scope_id` semantics — V1 implicit shared-cast parity vs conservative session-local default vs user-assigned continuity profile.

**Not recommended:** Direct migration of V1 `st.session_state` caches, wholesale transcript injection, or LLM memory consolidation.

---

## 22. Repository state

| Field | Value |
|-------|-------|
| Investigation commit | (pending) |
| Branch | `main` |

---

## 23. Next recommended implementation slice

**M10.1 — Session-local MemoryWritePolicy + ContextAssembly retrieval contributor**

- Wire `memory_layer/writes.py` policy to `DomainKernel.commit_move` and `record_user_turn`
- Persist updates through existing `SessionRepository` `CharacterState`
- Add `character_memory` contributions to `prepare_context` (deterministic tail)
- Tests: perception isolation (observer does not receive actor-private beats), session reopen restores episodic tails, no cross-session scope yet

**Governance review required before implementation.**
