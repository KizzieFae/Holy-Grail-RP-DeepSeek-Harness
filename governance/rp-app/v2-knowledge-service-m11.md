# V2 KnowledgeService Architecture — M11 Investigation Report

**Status:** Investigation complete — **no implementation authorized**  
**Date:** 2026-08-18  
**M10.2 anchor:** `ee0cff8`  
**M10.3 anchor:** `136c686`  
**Investigation HEAD:** (see §29 after commit)

**Governing principles:**

> Python Domain Host owns authoritative Holy Grail state, persistence, memory, knowledge, and context semantics.

> Preserve behavioral/domain value, not V1 runtime categories or storage structure.

> Continuity remains sole authority for in-scene established truth; knowledge assists inference.

---

## 1. Activation state

| Field | Value |
|-------|-------|
| Repository | `KizzieFae/Holy-Grail-RP-DeepSeek-Harness` |
| Branch | `main` |
| HEAD at investigation start | `136c686` |
| `origin/main` | Aligned |
| Working tree | Clean |
| Assigned / effective workflow weight | standard / **full** |
| Bootstrap profile | full V2 architecture investigation |
| Authorization | **Investigation/design only** |

**Validation:**

| Suite | Result |
|-------|--------|
| V2 Python (`v2/tests/`) | 67 passed |
| V2 Node (`v2/rp_runtime/tests/`) | 51 passed |

**Artifacts reviewed:** `CANONICAL_KNOWLEDGE_MODEL.md`, V1 `authored_retrieval_index.py`, `retrieved_context_select.py`, `prompt_retrieval_assembly.py`, `scene_grounding.py`, `continuity_canon_anchors.py`, `app_memory_summary.py`, `session_manager.py`, M9 `session_setup.py`, V2 `kernel.prepare_context`, M10.3 governance.

---

## 2. V1 knowledge/retrieval inventory

V1 knowledge-like material reaches prompts through **six distinct mechanisms** that must not be conflated.

### A. Continuity / canon (authoritative domain state)

| Mechanism | Location | Content | Authority | Visibility | Durable | Reaches prompts |
|-----------|----------|---------|-----------|------------|---------|-----------------|
| `ContinuityManager` state | `continuity_manager.py` | Issues, public events, interpretations, turn counter | **Canonical** | Role-filtered | Session JSON | `SUMMARY BLOCKS`, `ACTIVE ISSUES`, `RECENT PUBLIC EVENTS` |
| Canon anchors | `continuity_canon_anchors.py` | Seeded traits/voice + committed `world_fact` anchors | **Canonical** | Per-character via `get_relevant_canon_anchors` | Session continuity | `CANON ANCHORS` block |
| Scene grounding | `scene_grounding.py` | Settled facts from public-event markers | **Canonical (settled)** | Character prompts (binding subset) | Rebuilt each turn in `scene_grounding` | `SETTLED FACTS` / binding constraints |

**Classification:** Domain truth — **not KnowledgeService**. May **inform** learned-knowledge write policy but must not be duplicated as assistive knowledge.

### B. Authored static retrieval (compiled index)

| Mechanism | Location | Content | Authority | Visibility | Durable | Reaches prompts |
|-----------|----------|---------|-----------|------------|---------|-----------------|
| Authored retrieval index | `authored_retrieval_index.py`, env `RP_RETRIEVED_CONTEXT_INDEX` | Compiled chunks: character card slices, template notes, lore, setup | **Non-authoritative** (`non_authoritative=True`) | Per-character selection (`scope`, tags, template id) | External JSON file | Retrieved context section |
| Compile pipeline | `authored_index_compile.py`, `canonical_compile_adapters.py` | Maps card/template fields → canonical types | Compile-time ceilings per `CANONICAL_KNOWLEDGE_MODEL` | `visibility` in compile adapters | Recompiled from sources | Indirect |

**Caps:** 8 items / 8000 chars global; per-kind subcaps (lore 1×600, template 3, setup 2, character card 4).

**Classification:** **KnowledgeService core** — deterministic authored retrieval. Real product value.

### C. Character card lore (direct / private)

| Mechanism | Location | Content | Authority | Visibility | Durable | Reaches prompts |
|-----------|----------|---------|-----------|------------|---------|-----------------|
| `lore_facts` on card | Character JSON | Authored lore strings | Authored setup-truth / reference | Character-private in V1 patterns | Card file | Via compile index or private state |
| `private_memories` | `CharacterState` | Includes lore trail | Not prompt-injected (audit) | Character-only | Session | No |
| V2 interim | `session_setup.py` | First `lore_facts[0]` → `character_private_secrets` | Misclassified as private secret | Character-only | Session snapshot | `character_private` contribution |

**Classification:** Authored character knowledge — belongs in **KnowledgeService** with snapshot provenance, not ad-hoc private secret string.

### D. Cross-session memory buckets (misplaced knowledge)

| Mechanism | Location | Content | Authority | Visibility | Durable | Reaches prompts |
|-----------|----------|---------|-----------|------------|---------|-----------------|
| `persistent_world_facts` | `build_memory_buckets` at save | Canon anchors `category=world_fact` + location string | Canon-derived | **Broadcast to all cast** (unsafe) | Session index | `PERSISTENT WORLD FACTS` |
| `user_preferences` | `extract_user_preferences` regex | User chat heuristics | Weak derived | **Broadcast** | Session index | `USER PREFERENCES` |
| `session_summary` | Last chat snippet | Not real summary | Weak | Aggregated only | Index | **Not prompt-injected** |

**Classification:** Semantic value exists; **V1 mechanism obsolete**. Destination = KnowledgeService (+ UserProfile facet), not MemoryService (M10.3).

### E. Episodic compile lane (continuity-backed retrieval)

| Mechanism | Location | Content | Authority | Visibility | Durable | Reaches prompts |
|-----------|----------|---------|-----------|------------|---------|-----------------|
| `episodic_memory_compile/select` | `episodic_memory_*.py`, flag `RP_EPISODIC_MEMORY` | Templates from public events / interpretations | **Non-authoritative** | Per-character visibility | Session cache | Merged into retrieved bundle |

**Classification:** Continuity-backed **retrieval**, not KnowledgeService. Future: ContinuityRetrievalProvider or separate lane — not static knowledge store.

### F. Presentation / evidence (not knowledge)

| Mechanism | Content | Classification |
|-----------|---------|----------------|
| `chat_history` / M8 `rp_history` | Transcript | Evidence — may trigger writes, not knowledge authority |
| DSH inference logs | Execution evidence | Not knowledge |
| `st.session_state` caches | `cross_session_memories`, episodic cache | UI/runtime convenience |

### V2 current gap (baseline)

| V1 capability | V2 status |
|---------------|-----------|
| Continuity canon anchors in context | Partial — round summary only |
| Scene grounding | ❌ Not wired |
| Authored retrieval index | ❌ Not wired |
| Card `lore_facts` proper lane | ❌ First fact only as private secret |
| World facts / user preferences | ❌ Correctly absent (M10.3) |
| MemoryService | ✅ M10.2 relationship lane |

---

## 3. Knowledge semantic model

| Category | Definition | Owner | Overlap notes |
|----------|------------|-------|---------------|
| **Canonical world fact** | True in continuity/domain state now | **Continuity** | KnowledgeService may **reference** at retrieve time; must not duplicate mutable truth |
| **Authored world knowledge** | Creator-supplied setting/lore not yet committed | **KnowledgeService** (`world_rule`, `lore_reference`) | Distinct from live canon |
| **Character-authored knowledge** | Card lore, voice, goals the character may know | **KnowledgeService** | Snapshot at session create (M9) |
| **Scene grounding** | Settled environmental facts from play | **Continuity** (derived read model) | Prompt-facing; not a second store |
| **Learned world knowledge** | Facts established in play, durable across sessions | **KnowledgeService** (future write lane) | Scope-bound; distinct from character belief |
| **User profile/preference** | Stable user/player interaction facts | **KnowledgeService** (`user_profile` facet) | Not world canon |
| **Character memory** | What character remembers experiencing | **MemoryService** | Retrievable but not reclassified |
| **Presentation/history** | M8 `rp_history` | Transcript layer | Evidence only |
| **DSH execution evidence** | Inference traces | DSH | Not knowledge |

**Overlap rules:**

- Authored lore **about the world** ≠ canonical fact until continuity commits it.
- Character **belief** about a fact → MemoryService; **shared durable world fact** → KnowledgeService (after promotion policy).
- Scene **state** (location, present cast) → Continuity/SceneState, not KnowledgeService.

---

## 4. Authority model

### V2 ContextAssembly classes (today)

`authoritative` | `derived` | `suggestive` — used on `PromptContribution`.

### Canonical knowledge classes (`CANONICAL_KNOWLEDGE_MODEL`)

`foundational_truth` | `setup_truth` | `behavioral_guidance` | `interpretive_guidance` | `reference_only`

### Mapping to V2 contributions

| Canonical class | V2 `authority_class` | May contradict memory? | May contradict authored lore? |
|-----------------|----------------------|------------------------|----------------------------|
| Continuity / grounding | `authoritative` | Memory is subordinate | Authored loses for current scene |
| Learned world fact (promoted) | `authoritative` or `suggestive` | Memory may differ (belief vs fact) | Canon wins over lore |
| Authored setup truth | `suggestive` or `authoritative` (setup only) | Memory does not override | Superseded by continuity |
| Authored reference | `suggestive` | No | Reference only |
| User profile | `suggestive` | N/A | Not world truth |

### Precedence (factual claims)

```text
Continuity + scene grounding  >  promoted learned world knowledge  >  authored setup truth  >  memory (belief)  >  reference_only lore
```

**User preference** is authoritative **about the user** only, never about world state.

Retrieval ordering must **not** imply authority — `priority` is for cap drops only.

---

## 5. Continuity vs KnowledgeService boundary

| Belongs in Continuity | Belongs in KnowledgeService |
|-----------------------|----------------------------|
| Current scene state (location, presence, issues) | Authored card/template lore |
| Committed public events | Compiled retrieval index entries |
| Canon anchors as live domain objects | Learned world facts (promoted copies with provenance) |
| Scene grounding (read model over continuity) | User-global preferences/profile |
| Summary blocks | Reference material for inference |

**Rule:**

> If required for domain correctness **right now** and mutated by commits → Continuity.

> If durable reference/context that **informs** inference but is not live mutable state → KnowledgeService.

**Anti-pattern:** Saving canon anchors into `memory_buckets.persistent_world_facts` **and** continuity — V1 duplicates. V2 should **read** from continuity at retrieval or promote once to KnowledgeService with `source_domain_commit_id`, not both independently.

---

## 6. Character-card lore architecture

**Recommendation:** Normalize from **session `setup_snapshot`** at retrieval time (M9 semantics).

| Question | Answer |
|----------|--------|
| Lore character-private or world-shared? | **Per compile adapter** — `lore_facts` → `lore_reference`, `character_scoped` visibility |
| Two characters, same world fact? | May have **different** authored knowledge; shared world rules come from template/lore manifest with `scope_global` |
| Lore change after session create? | **No silent rewrite** — session uses snapshot card JSON |
| Snapshot vs live files? | **Session snapshot** for in-session knowledge; live files only for **new** sessions |
| V2 interim fix | Replace `lore_facts[0]` private-secret hack with KnowledgeService authored lane |

**Implementation shape:** KnowledgeService reads `setup_snapshot.character_cards[file_id]` → deterministic compile (reuse `canonical_compile_adapters` rules) → filter by `subject_character_file_id`.

---

## 7. Scene/template grounding architecture

| Layer | Owner | ContextAssembly |
|-------|-------|-----------------|
| **Active scene state** (location, premise, roles, presence) | Continuity `SceneState` | `scene_state` contribution (existing) |
| **Settled grounding facts** | Continuity-derived (`scene_grounding.py`) | New `scene_grounding` contribution, `authoritative` |
| **Template reference** (premise detail, slot docs, world rules) | KnowledgeService from `setup_snapshot.scene_template` | `scene_reference` lane, `suggestive` |

**Split model** — do not move live SceneState into KnowledgeService.

---

## 8. Learned world-fact policy (design only)

**Not every commit becomes knowledge.**

### Promotion candidates (deterministic)

| Source | Eligible? | Notes |
|--------|-----------|-------|
| Canon anchor `category=world_fact` on commit | **Yes** | Already authoritative; promote to scope-bound knowledge record with provenance |
| Scene grounding settled fact | **Maybe** | Prefer continuity projection; promote only if needed cross-session |
| Character episodic line | **No** | MemoryService |
| User preference regex | **No** | UserProfile lane |
| Session summary snippet | **No** | Reject |

### Scope

Learned world facts are **`scope_global` within continuity scope** (all characters in scope may receive **if** visibility rules say so). Character-specific beliefs remain MemoryService.

### Conceptual write flow (future)

```text
continuity commit / canon anchor upsert
    ↓
KnowledgeWritePolicy.evaluate_world_fact(candidate)
    ↓
scope + authority + dedupe checks
    ↓
KnowledgeRepository.append (idempotent knowledge_id)
```

**Failure:** Same as M10.2 — domain commit succeeds; knowledge projection best-effort.

---

## 9. User preference/profile classification

| Example | Semantic class | Destination | Visibility |
|---------|----------------|-------------|------------|
| "User prefers concise narration" | Application/UX preference | App settings or `user_profile` (out of RP canon) | User-global |
| "Call me Alex" | User identity | `user_profile` lane | Scope-global within continuity scope |
| "I don't like coffee" (user said aloud) | User profile fact | `user_profile` if promoted; relationship memory if character-specific learning | Per promotion rules |
| "Kizzie learned user hates coffee" | Character belief | **MemoryService** (character perceived) | Subject character only |

**Reject** V1 `extract_user_preferences` regex as authoritative. Replace with:

1. Explicit user profile fields (authored)
2. Deterministic promotion from **perceived** user lines (optional, strict)
3. Character-specific variants → MemoryService, not broadcast

**Service shape:** `UserProfile` as a **facet/lane inside KnowledgeService** initially — separate `UserProfileService` only if boundaries blur.

---

## 10. Scope/identity model

### Dimensions

| Dimension | ID | Used for |
|-----------|-----|----------|
| Session | `hg_session_id` | Authored snapshot boundary |
| Continuity / knowledge scope | **`memory_scope_id` (initial alias)** | Learned world facts, user profile, cross-scope knowledge |
| Subject character | `character_file_id` | Character-authored + character-visible learned items |
| Scene template | `scene_template_id` | Template-scoped lore filtering |
| User | `user_persona_id` (speaker string for now) | User profile entries |

### `memory_scope_id` as knowledge scope?

**Recommendation for V2:** Use `memory_scope_id` as the **initial `continuity_scope_id`** for KnowledgeService learned facts and user profile.

| Approach | Pros | Cons |
|----------|------|------|
| Reuse `memory_scope_id` | One opt-in scope; matches M10.2 | Name mismatch; memory-isolated scope might want shared world |
| Separate `continuity_scope_id` | Clear semantics | Two IDs for users to manage |

**Unresolved question (focused):** If product later needs **shared world knowledge** with **isolated character memory**, split IDs. Do not implement split in M11.1 — document alias and revisit at first learned-fact slice.

**Authored session knowledge** is scoped by **`hg_session_id` + setup_snapshot**, not `memory_scope_id`.

---

## 11. Visibility/privacy model

| Class | Meaning | Example |
|-------|---------|---------|
| `character_scoped` | Only subject `character_file_id` | Card lore, private tendencies |
| `scope_global` | Any character in scope/session policy | World rules, location fact |
| `role_scoped` | Characters with matching role slot | Template constraints |
| `scene_scoped` | Current session/scene only | Active premise detail |
| `user_profile` | Injected per character policy (usually all cast) | "Call me Alex" |
| `director_only` | Never character inference | N/A for KnowledgeService character retrieve |

**Enforcement:** Python retrieval filter **before** `PromptContribution` — never rely on model instructions alone.

Catalog APIs: expose `knowledge_id`, `knowledge_kind`, `scope_id`, `created_at` — **never** private content bodies.

---

## 12. Knowledge record contract

Minimum backend-independent record:

```text
knowledge_id          # deterministic hash
scope_id              # memory_scope_id or session-scoped marker
knowledge_kind        # authored_lore | world_rule | scene_reference | learned_world_fact | user_profile | ...
content               # bounded text
authority_class       # maps to PromptContribution authority
visibility            # character_scoped | scope_global | ...
subject_character_file_id?  # required for character_scoped
source_kind           # character_card | scene_template | canon_anchor | user_turn | ...
source_asset_id?      # file stem, template id
source_session_id?
source_domain_commit_id?
provenance            # structured metadata
created_at
supersedes_knowledge_id?  # optional; defer complex revision
```

Every record answers: origin, who may know, authority, scope.

Align with `CANONICAL_KNOWLEDGE_MODEL` envelope — V2 records are a runtime persistence projection of that contract.

---

## 13. KnowledgeService interface

```text
KnowledgeService
    retrieve_authored(session, character_file_id, ...) → list[KnowledgeRecord]
    retrieve_scope(scope_id, character_file_id, kinds, ...) → list[KnowledgeRecord]
    project_context(fixture, character_id, role) → list[(content, provenance)]  # for ContextAssembly
    list_scopes() → safe metadata only
    # future:
    promote_learned_fact(candidate) → KnowledgeRecord | None
    promote_user_profile(candidate) → KnowledgeRecord | None
```

**Not owned by KnowledgeService:** continuity mutation, DSH, UI, provider selection, vector indexing internals.

**May consume:** `setup_snapshot`, `ContinuityManager` (read-only for canon anchors), optional compiled index path.

**Must not consume:** MemoryService as authority source (one-way: memory ≠ knowledge promotion without explicit policy).

---

## 14. Storage options

| Option | Description | Verdict |
|--------|-------------|---------|
| **A — File-backed repository** | JSON per scope/session for learned facts | **Preferred for learned facts (M11.2)** |
| **E — Authored sources + index abstraction** | Read session snapshot + optional `RP_RETRIEVED_CONTEXT_INDEX` | **Preferred for M11.1 authored** |
| **F — Hybrid authored + learned** | Snapshot compile at retrieve + file store for promotions | **Target architecture** |
| **B — SQLite** | Structured local index | Defer until query needs exceed file glob |
| **C — SQL + vector** | Future | Phase 4+ per `CANONICAL_KNOWLEDGE_MODEL` |
| **D — Graph** | Entity traversal | Not justified |

**Preferred backend-independent architecture:**

```text
KnowledgeService
    ├── AuthoredKnowledgeProvider (session snapshot + optional compiled index)
    ├── LearnedKnowledgeRepository (file-backed, scope-keyed)  # M11.2+
    └── UserProfileRepository (file-backed or scope JSON facet)  # M11.2+
```

---

## 15. Deterministic retrieval semantics

### Authored (M11.1)

Reuse V1 selection rules from `retrieved_selection_authored.py`:

- Filter by `character_file_id` / display name map
- Template id match for template + world lore tags
- Relationship-focus tag boost
- Dedupe by `source_ref` + text hash
- Per-kind subcaps then global cap
- Dedup against continuity text already in prompt

### Learned (M11.2+)

- Filter: `scope_id` + visibility + `knowledge_kind`
- Sort: authority tier DESC, `created_at` ASC
- Cap per kind: world facts 8, user profile 6
- Exclude items already present in continuity anchors for same statement hash

### No LLM ranking in initial implementation.

---

## 16. Vector/semantic retrieval assessment

| Question | Answer |
|----------|--------|
| Expected record count (near term) | Tens per scope, low hundreds authored index |
| Tags/filters sufficient? | **Yes** for M11 |
| Long lore corpora benefit? | **Later** — compiled index + caps work for card/template scale |
| Categories benefiting from vectors | Dense novel ingestion (Phase 4), not Holy Grail card/template scale |
| Pre-filter before vector rank? | **Required** — authority + visibility filters first |

**Future seam:**

```text
RetrievalProvider interface
    deterministic_select(query) → records
    semantic_select(query, embedding) → records  # optional plugin
```

Defer embeddings. `CANONICAL_KNOWLEDGE_MODEL` already defines conformance.

---

## 17. ContextAssembly integration

```text
prepare_context
    ├── scene_state (authoritative)           # existing
    ├── scene_grounding (authoritative)       # continuity-derived, future
    ├── authored_character_knowledge          # KnowledgeService, suggestive
    ├── scene_reference                       # template/world authored, suggestive
    ├── learned_world_knowledge               # KnowledgeService, authoritative/suggestive
    ├── user_profile                          # KnowledgeService facet, suggestive
    ├── character_memory                      # MemoryService, derived
    └── character_private                     # shrink — lore moves to knowledge lane
```

New `source_kind` values needed: `authored_knowledge`, `world_knowledge`, `scene_reference`, `user_profile`.

Separate contributions preserve provenance, caps, and debugging.

---

## 18. Token-budgeting policy

| Lane | Mandatory? | Cap (initial) |
|------|------------|---------------|
| Scene state / grounding | Yes | Continuity caps |
| Authored character | Yes (identity/lore) | 4 items / ~2k chars |
| Scene reference | Optional | 3 items |
| Learned world facts | Selective | 8 items / scope |
| User profile | Selective | 6 items |
| Authored lore excerpt | Optional | 1×600 chars (V1 parity) |

**Principles:** mandatory correctness lanes first; deterministic truncation; never consume entire window with reference material.

---

## 19. MemoryService relationship

```text
MemoryService   = what this character remembers (experienced belief)
KnowledgeService = what reference/world/user information is available
Continuity      = what is true now
```

| Direction | Allowed? |
|-----------|----------|
| Knowledge → Memory | **No** automatic |
| Memory → Knowledge | **No** — promotion requires explicit KnowledgeWritePolicy on domain events |
| Both → ContextAssembly | **Yes** — separate lanes |

Character-specific learned **belief** stays MemoryService unless elevated to scope-global **world fact** through canon anchor + promotion policy.

---

## 20. Session snapshot/version semantics

| Category | Source at retrieve |
|----------|-------------------|
| Character card fields | `setup_snapshot.character_cards` (immutable) |
| Scene template | `setup_snapshot.scene_template` |
| Compiled global index | Optional env path — **not** session-bound; use for dev/tools initially |
| Learned facts | `LearnedKnowledgeRepository` keyed by `scope_id` |
| User profile | `scope_id` + `user_persona_id` |

**Rule:** Historical sessions never read live card files for authored knowledge. Asset version = snapshot content hash in provenance.

---

## 21. V1 world-fact migration map

| V1 source | Semantic class | V2 destination | Action |
|-----------|----------------|--------------|--------|
| Canon anchor `world_fact` in continuity | Canonical | Continuity (primary) + optional KnowledgeService promotion | **Recompute** on retrieve or promote on commit |
| `Recent recurring location: …` | Scene metadata | Continuity SceneState.location | **Reject** as knowledge bucket |
| Cross-session `persistent_world_facts` aggregation | Misplaced canon | KnowledgeService `learned_world_fact` | **Do not migrate buckets** — recompute from continuity |
| Session index bucket copy | Denormalized cache | Obsolete | **Reject** |

---

## 22. V1 user-preference migration map

| V1 source | Semantic class | V2 destination | Action |
|-----------|----------------|--------------|--------|
| Regex `i like` / `call me` on user chat | Mixed | User profile promotion (strict) | **Reimplement** with perception + explicit rules |
| Fallback `User goes by {name}` | Identity default | Session `speaker` / user_profile | **Reject** weak fallback as knowledge |
| Cross-session preference broadcast | Unsafe global | `user_profile` scope-bound | **Reject** broadcast |
| Character-learned preference | Belief | MemoryService relationship/history | **Keep** in memory lane |

---

## 23. Optional tools/skills assessment

| Tool (future) | Legitimate? | Prerequisite |
|---------------|-------------|--------------|
| `search_world_lore` | Optional deep lookup | Large corpora + vector provider |
| `lookup_location` | Maybe | Location knowledge index |
| `lookup_character_reference` | Maybe | Authored index |

**Rule:** Mandatory correctness knowledge → deterministic `KnowledgeService.retrieve`. Tools only for optional reference depth.

Do not implement in M11.

---

## 24. UI-safe boundary

| API | Safe metadata | Hidden |
|-----|---------------|--------|
| `GET /v1/catalog/knowledge-scopes` | `scope_id`, `created_at`, record counts by kind | Content |
| Session create | `memory_scope_id` (existing) | — |
| Debug (future) | Provenance ids, kinds | Private character lore bodies in UI lists |

Streamlit: no knowledge browser in M11.

---

## 25. V1 retirement impact

| V1 responsibility | V2 replacement | Removal condition |
|-------------------|----------------|-------------------|
| `build_memory_buckets.persistent_world_facts` | KnowledgeService + continuity read | M11.2 complete |
| `build_memory_buckets.user_preferences` | User profile facet | M11.2 complete |
| `get_cross_session_memories` world/pref buckets | Scope-bound KnowledgeService | V2-only |
| `RP_RETRIEVED_CONTEXT_INDEX` in Streamlit path | KnowledgeService authored provider | V2 ContextAssembly wired |
| `lore_facts[0]` private secret hack (V2) | `authored_character_knowledge` lane | M11.1 |
| Prompt-builder direct lore injection | KnowledgeService projections | V1 path unused |
| Episodic merge in retrieval | Continuity retrieval lane (future) | Separate slice |

---

## 26. Recommended implementation sequence

| Slice | Scope | Proves |
|-------|-------|--------|
| **M11.1** | KnowledgeService interface + **authored** retrieval from session snapshot (+ optional compiled index) + ContextAssembly lanes | Visibility, authority, snapshot semantics, lore fix |
| **M11.2** | Scope-bound **learned world facts** + **user profile** repositories + KnowledgeWritePolicy on canon/user events | M10.3 migration target |
| **M11.3** | Scene grounding + canon anchor ContextAssembly (continuity-derived authoritative) | Continuity/knowledge boundary |
| **M11.4+** | Episodic continuity retrieval; vector provider | Only if evidenced |

**Do not** start with SQLite or vectors.

---

## 27. Challenge/refinement

| Challenge | Response |
|-----------|----------|
| Duplicating continuity into KnowledgeService? | **Reject** — read or promote once with provenance |
| Authored lore mistaken for canon? | `suggestive` / `reference_only` classes |
| Private facts visibility-safe? | Filter by `character_file_id` before manifest |
| User preferences actually knowledge? | **User profile facet**, not memory |
| `memory_scope_id` doubles as knowledge scope? | **Yes initially**; document split risk |
| Snapshot semantics clear? | M9 snapshot authoritative for authored |
| Deterministic retrieval enough? | **Yes** at current scale |
| Vectors justified? | **No** for M11 |
| KnowledgeService catch-all? | **Rejected** — continuity/memory boundaries enforced |
| Simpler than V1? | **Yes** — explicit lanes vs bucket broadcast |
| DB without DSH change? | **Yes** — behind KnowledgeService |
| V1 value preserved? | Authored retrieval + canon; weak buckets dropped |
| Clean V1 retirement? | **Yes** with mapped destinations |

---

## 28. Architecture verdict

**Mature KnowledgeService architecture established with one focused unresolved question:**

> Should `memory_scope_id` remain the sole continuity scope for learned knowledge, or will product require split memory vs world-scope IDs?

All other boundaries are sufficiently defined to begin implementation.

---

## 29. Repository state

| Item | Value |
|------|-------|
| Investigation commit | (this document) |
| Runtime changes | **None** |

---

## 30. Next recommended implementation slice

**M11.1 — KnowledgeService interface + authored character/template knowledge retrieval from session snapshot** (Governance review required).

Deliverables:

- `KnowledgeService` + `AuthoredKnowledgeProvider` (snapshot compile, visibility filter)
- ContextAssembly contributions: `authored_character_knowledge`, `scene_reference`
- Replace `lore_facts[0]` private-secret workaround
- Deterministic tests: snapshot isolation, character visibility, template-scoped lore, no live-card bleed
- **No** learned world facts, user profile write path, database, or vectors

Do not implement without Governance review.
